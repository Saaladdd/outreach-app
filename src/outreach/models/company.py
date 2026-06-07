from pydantic import BaseModel, Field


class CompanyDomain(BaseModel):
    domain: str
    name: str | None = None
    industry: str | None = None
    employee_count: str | None = None

    @property
    def display_name(self) -> str:
        return self.name or self.domain
