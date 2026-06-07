import logging

from brevo import Brevo
from brevo.transactional_emails import (
    SendTransacEmailRequestSender,
    SendTransacEmailRequestToItem,
)

from outreach.config import Settings
from outreach.models.contact import ComposedEmail, SendResult

logger = logging.getLogger(__name__)


class BrevoClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: Brevo | None = None

    def _get_client(self) -> Brevo:
        if self._client is None:
            self._client = Brevo(api_key=self.settings.brevo_api_key)
        return self._client

    def send_email(self, composed: ComposedEmail, dry_run: bool = False) -> SendResult:
        contact = composed.contact
        if dry_run:
            return SendResult(
                contact=contact,
                success=True,
                message_id="dry-run",
            )

        try:
            result = self._get_client().transactional_emails.send_transac_email(
                subject=composed.subject,
                html_content=composed.html_body,
                text_content=composed.text_body or None,
                sender=SendTransacEmailRequestSender(
                    email=self.settings.brevo_sender_email,
                    name=self.settings.brevo_sender_name,
                ),
                to=[
                    SendTransacEmailRequestToItem(
                        email=contact.email,
                        name=contact.full_name,
                    )
                ],
            )
            return SendResult(
                contact=contact,
                success=True,
                message_id=str(getattr(result, "message_id", None) or result),
            )
        except Exception as exc:
            logger.error("Brevo send failed for %s: %s", contact.email, exc)
            return SendResult(contact=contact, success=False, error=str(exc))

    def send_all(
        self, emails: list[ComposedEmail], dry_run: bool = False
    ) -> list[SendResult]:
        return [self.send_email(email, dry_run=dry_run) for email in emails]
