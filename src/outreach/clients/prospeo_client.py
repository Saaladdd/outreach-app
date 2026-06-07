import logging

import httpx

from outreach.config import Settings
from outreach.models.contact import Contact
from outreach.services.dedupe import normalize_domain
from outreach.services.rate_limit import sleep_between_requests, with_retries

logger = logging.getLogger(__name__)

PROSPEO_BASE = "https://api.prospeo.io"
WEBSITE_BATCH_SIZE = 500
SENIORITY_FILTER = ["C-Suite", "Vice President"]


class ProspeoClient:
    def __init__(self, settings: Settings, http: httpx.Client | None = None) -> None:
        self.settings = settings
        self._http = http or httpx.Client(timeout=60.0)

    def close(self) -> None:
        self._http.close()

    def _headers(self) -> dict[str, str]:
        return {
            "X-KEY": self.settings.prospeo_api_key,
            "Content-Type": "application/json",
        }

    @with_retries()
    def _search_page(self, websites: list[str], page: int, max_per_company: int) -> dict:
        payload = {
            "page": page,
            "filters": {
                "company": {"websites": {"include": websites}},
                "person_seniority": {"include": SENIORITY_FILTER},
                "max_person_per_company": max_per_company,
            },
        }
        response = self._http.post(
            f"{PROSPEO_BASE}/search-person",
            headers=self._headers(),
            json=payload,
        )
        if response.status_code == 400:
            body = response.json()
            if body.get("error_code") == "NO_RESULTS":
                return {"results": [], "pagination": {"total_page": 0}}
        response.raise_for_status()
        return response.json()

    def find_decision_makers(
        self,
        domains: list[str],
        max_per_company: int = 1,
        max_pages_per_batch: int = 5,
    ) -> list[Contact]:
        normalized = [normalize_domain(d) for d in domains if d]
        contacts: list[Contact] = []

        for i in range(0, len(normalized), WEBSITE_BATCH_SIZE):
            batch = normalized[i : i + WEBSITE_BATCH_SIZE]
            page = 1
            total_pages = 1

            while page <= total_pages and page <= max_pages_per_batch:
                try:
                    data = self._search_page(batch, page, max_per_company)
                except httpx.HTTPStatusError as exc:
                    logger.error("Prospeo search failed on page %s: %s", page, exc)
                    break

                pagination = data.get("pagination") or {}
                total_pages = pagination.get("total_page") or 0

                for row in data.get("results") or []:
                    contact = self._map_contact(row)
                    if contact and contact.linkedin_url:
                        contacts.append(contact)

                if page >= total_pages:
                    break
                page += 1
                sleep_between_requests(self.settings.request_delay_seconds)

        return contacts

    def _map_contact(self, row: dict) -> Contact | None:
        person = row.get("person") or {}
        company = row.get("company") or {}
        linkedin = (
            person.get("linkedin_url")
            or person.get("linkedin")
            or (person.get("socials") or {}).get("linkedin")
        )
        if not linkedin:
            return None

        website = company.get("website") or company.get("domain") or ""
        return Contact(
            person_id=person.get("person_id") or person.get("id"),
            first_name=person.get("first_name") or "",
            last_name=person.get("last_name") or "",
            title=person.get("job_title") or person.get("title") or "",
            linkedin_url=linkedin,
            company_domain=normalize_domain(website) if website else "",
            company_name=company.get("name"),
        )
