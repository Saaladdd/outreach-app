from datetime import datetime, timezone

from pydantic import BaseModel, Field

from outreach.models.company import CompanyDomain
from outreach.models.contact import (
    ComposedEmail,
    Contact,
    EnrichedContact,
    SendResult,
    StageError,
)


class PipelineRun(BaseModel):
    seed_domain: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    mock_mode: bool = False
    dry_run: bool = False

    companies: list[CompanyDomain] = Field(default_factory=list)
    contacts: list[Contact] = Field(default_factory=list)
    enriched_contacts: list[EnrichedContact] = Field(default_factory=list)
    composed_emails: list[ComposedEmail] = Field(default_factory=list)
    send_results: list[SendResult] = Field(default_factory=list)
    errors: list[StageError] = Field(default_factory=list)

    def add_error(self, stage: str, message: str, **context: object) -> None:
        self.errors.append(StageError(stage=stage, message=message, context=context))
