import logging

from outreach.clients.prospeo_client import ProspeoClient
from outreach.models.company import CompanyDomain
from outreach.models.contact import Contact, StageError
from outreach.stages.base import StageResult

logger = logging.getLogger(__name__)


class ProspeoStage:
    def __init__(self, client: ProspeoClient) -> None:
        self.client = client

    def run(
        self,
        companies: list[CompanyDomain],
        max_per_company: int = 1,
    ) -> StageResult[Contact]:
        result = StageResult[Contact]()
        domains = [c.domain for c in companies]
        if not domains:
            result.errors.append(
                StageError(stage="prospeo", message="No company domains to search")
            )
            return result

        try:
            result.data = self.client.find_decision_makers(
                domains, max_per_company=max_per_company
            )
            logger.info("Prospeo found %s contacts", len(result.data))
        except Exception as exc:
            logger.exception("Prospeo stage failed")
            result.errors.append(StageError(stage="prospeo", message=str(exc)))
        return result
