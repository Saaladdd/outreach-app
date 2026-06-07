from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from outreach.models.contact import StageError

T = TypeVar("T")


class StageResult(BaseModel, Generic[T]):
    data: list[T] = Field(default_factory=list)
    errors: list[StageError] = Field(default_factory=list)
    skipped: int = 0

    @property
    def success_count(self) -> int:
        return len(self.data)
