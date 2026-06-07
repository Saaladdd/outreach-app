import logging

from outreach.clients.brevo_client import BrevoClient
from outreach.models.contact import ComposedEmail, SendResult, StageError
from outreach.stages.base import StageResult

logger = logging.getLogger(__name__)


class BrevoStage:
    def __init__(self, client: BrevoClient) -> None:
        self.client = client

    def run(
        self, emails: list[ComposedEmail], dry_run: bool = False
    ) -> StageResult[SendResult]:
        result = StageResult[SendResult]()
        if not emails:
            result.errors.append(StageError(stage="brevo", message="No emails to send"))
            return result

        try:
            result.data = self.client.send_all(emails, dry_run=dry_run)
            sent = sum(1 for r in result.data if r.success)
            logger.info("Brevo sent %s/%s emails", sent, len(result.data))
        except Exception as exc:
            logger.exception("Brevo stage failed")
            result.errors.append(StageError(stage="brevo", message=str(exc)))
        return result
