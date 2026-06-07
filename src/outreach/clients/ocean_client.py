import logging

import httpx

from outreach.config import Settings
from outreach.models.company import CompanyDomain
from outreach.services.dedupe import normalize_domain
from outreach.services.rate_limit import sleep_between_requests, with_retries

logger = logging.getLogger(__name__)

OCEAN_BASE = "https://api.ocean.io"


class OceanClient:
    def __init__(self, settings: Settings, http: httpx.Client | None = None) -> None:
        self.settings = settings
        self._http = http or httpx.Client(timeout=60.0)

    def close(self) -> None:
        self._http.close()

    def _headers(self) -> dict[str, str]:
        return {
            "X-Api-Token": self.settings.ocean_api_token,
            "Content-Type": "application/json",
        }

    @with_retries()
    def _post(self, path: str, payload: dict) -> dict:
        response = self._http.post(
            f"{OCEAN_BASE}{path}",
            headers=self._headers(),
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    def validate_seed_domain(self, seed_domain: str) -> str:
        """Normalize seed via autocomplete when possible."""
        normalized = normalize_domain(seed_domain)
        try:
            data = self._post(
                "/v2/autocomplete/companies",
                {"name": normalized, "forLookalikeSearch": True},
            )
            companies = data.get("companies") or []
            for company in companies:
                domain = company.get("domain", "")
                if normalize_domain(domain) == normalized or normalized in domain:
                    return normalize_domain(domain)
            if companies:
                return normalize_domain(companies[0]["domain"])
        except Exception as exc:
            logger.warning("Ocean autocomplete failed, using raw domain: %s", exc)
        return normalized

    def find_lookalikes(self, seed_domain: str, max_companies: int) -> list[CompanyDomain]:
        seed = self.validate_seed_domain(seed_domain)
        companies: list[CompanyDomain] = []
        search_after: str | None = None

        while len(companies) < max_companies:
            page_size = min(100, max_companies - len(companies))
            payload: dict = {
                "size": page_size,
                "companiesFilters": {
                    "lookalikeDomains": [seed],
                    "excludeDomains": [seed],
                    "companyMatchingMode": "precise",
                },
            }
            if search_after:
                payload["searchAfter"] = search_after

            data = self._post("/v3/search/companies", payload)
            for item in data.get("companies") or []:
                domain = item.get("domain")
                if not domain:
                    continue
                companies.append(
                    CompanyDomain(
                        domain=normalize_domain(domain),
                        name=item.get("name"),
                        industry=(item.get("industry") or {}).get("name")
                        if isinstance(item.get("industry"), dict)
                        else item.get("industry"),
                        employee_count=item.get("companySize"),
                    )
                )
                if len(companies) >= max_companies:
                    break

            search_after = data.get("searchAfter")
            if not search_after:
                break
            sleep_between_requests(self.settings.request_delay_seconds)

        return companies
