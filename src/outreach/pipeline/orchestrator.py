import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from outreach.clients.brevo_client import BrevoClient
from outreach.clients.eazyreach_client import EazyreachClient
from outreach.clients.ocean_client import OceanClient
from outreach.clients.prospeo_client import ProspeoClient
from outreach.config import Settings
from outreach.mocks.mock_clients import (
    MockBrevoClient,
    MockEazyreachClient,
    MockOceanClient,
    MockProspeoClient,
)
from outreach.models.pipeline_state import PipelineRun
from outreach.pipeline.checkpoint import confirm_send, show_checkpoint_summary
from outreach.services.dedupe import dedupe_by, normalize_domain
from outreach.services.email_composer import EmailComposer
from outreach.stages.brevo_stage import BrevoStage
from outreach.stages.eazyreach_stage import EazyreachStage
from outreach.stages.ocean_stage import OceanStage
from outreach.stages.prospeo_stage import ProspeoStage

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    def __init__(
        self,
        settings: Settings,
        *,
        mock: bool = False,
        dry_run: bool = False,
        use_llm: bool = False,
    ) -> None:
        self.settings = settings
        self.mock = mock
        self.dry_run = dry_run
        self.use_llm = use_llm
        self._clients: list = []

        if mock:
            ocean = MockOceanClient(settings)
            prospeo = MockProspeoClient(settings)
            eazyreach = MockEazyreachClient(settings)
            brevo = MockBrevoClient(settings)
        else:
            ocean = OceanClient(settings)
            prospeo = ProspeoClient(settings)
            eazyreach = EazyreachClient(settings)
            brevo = BrevoClient(settings)
            self._clients.extend([ocean, prospeo, eazyreach])

        self.ocean_stage = OceanStage(ocean)
        self.prospeo_stage = ProspeoStage(prospeo)
        self.eazyreach_stage = EazyreachStage(eazyreach)
        self.brevo_stage = BrevoStage(brevo)
        self.composer = EmailComposer(settings, use_llm=use_llm)

    def close(self) -> None:
        for client in self._clients:
            if hasattr(client, "close"):
                client.close()

    def run(
        self,
        seed_domain: str,
        *,
        max_companies: int = 25,
        max_contacts_per_company: int = 1,
        confirm_send_flag: bool = False,
        save_run: bool = False,
    ) -> PipelineRun:
        run = PipelineRun(
            seed_domain=normalize_domain(seed_domain),
            mock_mode=self.mock,
            dry_run=self.dry_run,
        )

        try:
            ocean_result = self.ocean_stage.run(run.seed_domain, max_companies)
            run.companies = ocean_result.data
            run.errors.extend(ocean_result.errors)
            if not run.companies and ocean_result.errors:
                return self._finalize(run, save_run)

            prospeo_result = self.prospeo_stage.run(
                run.companies, max_per_company=max_contacts_per_company
            )
            run.contacts = dedupe_by(
                prospeo_result.data,
                key_fn=lambda c: c.linkedin_url,
            )
            run.errors.extend(prospeo_result.errors)

            eazyreach_result = self.eazyreach_stage.run(run.contacts)
            run.enriched_contacts = dedupe_by(
                eazyreach_result.data,
                key_fn=lambda c: c.email,
            )
            run.errors.extend(eazyreach_result.errors)

            if not run.enriched_contacts:
                run.add_error("pipeline", "No contacts with verified emails to mail")
                return self._finalize(run, save_run)

            run.composed_emails = self.composer.compose_all(
                run.enriched_contacts, run.seed_domain
            )

            show_checkpoint_summary(run.seed_domain, run.composed_emails, self.dry_run)
            if not confirm_send(confirm_send_flag):
                run.add_error("checkpoint", "Send cancelled by user")
                return self._finalize(run, save_run)

            send_dry_run = self.dry_run or self.mock
            brevo_result = self.brevo_stage.run(run.composed_emails, dry_run=send_dry_run)
            run.send_results = brevo_result.data
            run.errors.extend(brevo_result.errors)

        finally:
            self.close()

        return self._finalize(run, save_run)

    def _finalize(self, run: PipelineRun, save_run: bool) -> PipelineRun:
        run.finished_at = datetime.now(timezone.utc)
        if save_run:
            self._persist_run(run)
        return run

    def _persist_run(self, run: PipelineRun) -> None:
        out_dir = Path("runs")
        out_dir.mkdir(exist_ok=True)
        ts = run.started_at.strftime("%Y%m%d_%H%M%S")
        path = out_dir / f"run_{ts}.json"
        path.write_text(run.model_dump_json(indent=2), encoding="utf-8")
        logger.info("Saved run artifact to %s", path)
