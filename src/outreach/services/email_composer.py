import json
import logging
import re

from openai import OpenAI

from outreach.config import Settings
from outreach.models.contact import ComposedEmail, EnrichedContact

logger = logging.getLogger(__name__)

DEFAULT_SUBJECT = "Quick idea for {{company}}"

DEFAULT_HTML = """\
<p>Hi {{first_name}},</p>
<p>I noticed your work as {{title}} at {{company}} and thought this might be relevant.</p>
<p>{{pitch}}</p>
<p>Would you be open to a 15-minute chat this week?</p>
<p>Best,<br>{{sender_name}}</p>
"""


class EmailComposer:
    def __init__(self, settings: Settings, use_llm: bool = False) -> None:
        self.settings = settings
        self.use_llm = use_llm and bool(settings.openai_api_key)

    def compose_all(
        self, contacts: list[EnrichedContact], seed_domain: str
    ) -> list[ComposedEmail]:
        return [self.compose_one(c, seed_domain) for c in contacts]

    def compose_one(self, contact: EnrichedContact, seed_domain: str) -> ComposedEmail:
        if self.use_llm:
            try:
                return self._compose_with_llm(contact, seed_domain)
            except Exception as exc:
                logger.warning("LLM compose failed for %s: %s", contact.email, exc)
        return self._compose_with_template(contact)

    def _compose_with_template(self, contact: EnrichedContact) -> ComposedEmail:
        company = contact.company_name or contact.company_domain
        replacements = {
            "{{first_name}}": contact.first_name or "there",
            "{{title}}": contact.title or "your role",
            "{{company}}": company,
            "{{pitch}}": self.settings.product_pitch,
            "{{sender_name}}": self.settings.brevo_sender_name,
        }
        subject = DEFAULT_SUBJECT
        html = DEFAULT_HTML
        for token, value in replacements.items():
            subject = subject.replace(token, value)
            html = html.replace(token, value)
        text = re.sub(r"<[^>]+>", "", html)
        return ComposedEmail(
            contact=contact,
            subject=subject,
            html_body=html,
            text_body=text,
        )

    def _compose_with_llm(self, contact: EnrichedContact, seed_domain: str) -> ComposedEmail:
        client_kwargs: dict = {"api_key": self.settings.openai_api_key}
        if self.settings.openai_base_url:
            client_kwargs["base_url"] = self.settings.openai_base_url
        client = OpenAI(**client_kwargs)

        company = contact.company_name or contact.company_domain
        prompt = f"""Write a short, personalized B2B cold outreach email.

Recipient: {contact.full_name}, {contact.title} at {company}
Seed customer domain (we sell to companies like): {seed_domain}
Product pitch: {self.settings.product_pitch}
Sender name: {self.settings.brevo_sender_name}

Return JSON only with keys: subject, html_body (short HTML, under 120 words)."""

        response = client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        content = response.choices[0].message.content or "{}"
        payload = json.loads(content)
        html = payload.get("html_body", "")
        subject = payload.get("subject", f"Quick idea for {company}")
        text = re.sub(r"<[^>]+>", "", html)
        return ComposedEmail(
            contact=contact,
            subject=subject,
            html_body=html,
            text_body=text,
        )
