import logging
import time

import httpx

from outreach.config import Settings
from outreach.models.contact import Contact, EnrichedContact
from outreach.services.rate_limit import sleep_between_requests, with_retries

logger = logging.getLogger(__name__)

# Adjust path/query keys once Eazyreach dashboard docs are confirmed.
LINKEDIN_TO_EMAIL_PATH = "/v1/enrich/linkedin-email"


class EazyreachClient:
    def __init__(self, settings: Settings, http: httpx.Client | None = None) -> None:
        self.settings = settings
        self._http = http or httpx.Client(timeout=90.0)

    def close(self) -> None:
        self._http.close()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.settings.eazyreach_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _base_url(self) -> str:
        return self.settings.eazyreach_base_url.rstrip("/")

    @with_retries()
    def _request_email(self, linkedin_url: str) -> httpx.Response:
        return self._http.post(
            f"{self._base_url()}{LINKEDIN_TO_EMAIL_PATH}",
            headers=self._headers(),
            json={"linkedin_url": linkedin_url},
        )

    def resolve_email(self, contact: Contact, max_polls: int = 5) -> EnrichedContact | None:
        linkedin_url = contact.linkedin_url.strip()
        if not linkedin_url:
            return None

        for attempt in range(max_polls):
            try:
                response = self._request_email(linkedin_url)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    logger.info("No email for %s", linkedin_url)
                    return None
                raise

            if response.status_code == 202:
                retry_after = int(response.headers.get("Retry-After", "3"))
                time.sleep(retry_after)
                continue

            if response.status_code == 404:
                logger.info("No email for %s", linkedin_url)
                return None

            response.raise_for_status()
            data = response.json()
            email = data.get("email") or data.get("work_email") or ""
            if not email and data.get("found") is False:
                return None
            if not email:
                return None

            return EnrichedContact(
                **contact.model_dump(),
                email=email,
                email_status=data.get("status") or "verified",
            )

        logger.warning("Eazyreach timed out polling for %s", linkedin_url)
        return None

    def resolve_all(self, contacts: list[Contact]) -> tuple[list[EnrichedContact], int]:
        enriched: list[EnrichedContact] = []
        skipped = 0
        for contact in contacts:
            result = self.resolve_email(contact)
            if result:
                enriched.append(result)
            else:
                skipped += 1
            sleep_between_requests(self.settings.request_delay_seconds)
        return enriched, skipped
