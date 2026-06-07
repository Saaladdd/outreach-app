import json
from pathlib import Path

from outreach.clients.brevo_client import BrevoClient
from outreach.clients.eazyreach_client import EazyreachClient
from outreach.clients.ocean_client import OceanClient
from outreach.clients.prospeo_client import ProspeoClient
from outreach.config import Settings
from outreach.models.company import CompanyDomain
from outreach.models.contact import Contact, EnrichedContact

FIXTURES = Path(__file__).parent / "fixtures"


def _load_json(name: str):
    with open(FIXTURES / name, encoding="utf-8") as f:
        return json.load(f)


class MockOceanClient(OceanClient):
    def find_lookalikes(self, seed_domain: str, max_companies: int) -> list[CompanyDomain]:
        data = _load_json("ocean_companies.json")
        companies = [CompanyDomain(**item) for item in data]
        return companies[:max_companies]


class MockProspeoClient(ProspeoClient):
    def find_decision_makers(
        self,
        domains: list[str],
        max_per_company: int = 1,
        max_pages_per_batch: int = 5,
    ) -> list[Contact]:
        data = _load_json("prospeo_contacts.json")
        contacts = [Contact(**item) for item in data]
        domain_set = {d.lower() for d in domains}
        return [c for c in contacts if c.company_domain.lower() in domain_set]


class MockEazyreachClient(EazyreachClient):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._email_map = _load_json("eazyreach_emails.json")

    def close(self) -> None:
        pass

    def resolve_email(self, contact: Contact, max_polls: int = 5) -> EnrichedContact | None:
        entry = self._email_map.get(contact.linkedin_url)
        if not entry:
            return None
        return EnrichedContact(
            **contact.model_dump(),
            email=entry["email"],
            email_status=entry.get("status", "verified"),
        )


class MockBrevoClient(BrevoClient):
    def send_email(self, composed, dry_run: bool = False):
        from outreach.models.contact import SendResult

        return SendResult(
            contact=composed.contact,
            success=True,
            message_id="mock-message-id",
        )
