import logging

from outreach.clients.eazyreach_client import EazyreachClient
from outreach.models.contact import Contact, EnrichedContact, StageError
from outreach.stages.base import StageResult

logger = logging.getLogger(__name__)


class EazyreachStage:
    def __init__(self, client: EazyreachClient) -> None:
        self.client = client

    def run(self, contacts: list[Contact]) -> StageResult[EnrichedContact]:
        result = StageResult[EnrichedContact]()
        if not contacts:
            result.errors.append(
                StageError(stage="eazyreach", message="No contacts to enrich")
            )
            return result

        try:
            enriched, skipped = self.client.resolve_all(contacts)
            result.data = enriched
            result.skipped = skipped
            logger.info(
                "Eazyreach enriched %s contacts (%s skipped)",
                len(result.data),
                skipped,
            )
        except Exception as exc:
            logger.exception("Eazyreach stage failed")
            result.errors.append(StageError(stage="eazyreach", message=str(exc)))
        return result
