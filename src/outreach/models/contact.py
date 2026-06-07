from pydantic import BaseModel, Field


class Contact(BaseModel):
    person_id: str | None = None
    first_name: str = ""
    last_name: str = ""
    title: str = ""
    linkedin_url: str = ""
    company_domain: str = ""
    company_name: str | None = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or "there"


class EnrichedContact(Contact):
    email: str = ""
    email_status: str = "unknown"


class ComposedEmail(BaseModel):
    contact: EnrichedContact
    subject: str
    html_body: str
    text_body: str = ""


class SendResult(BaseModel):
    contact: EnrichedContact
    success: bool
    message_id: str | None = None
    error: str | None = None


class StageError(BaseModel):
    stage: str
    message: str
    context: dict = Field(default_factory=dict)
