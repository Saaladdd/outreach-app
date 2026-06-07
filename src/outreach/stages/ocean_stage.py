import logging

from outreach.clients.ocean_client import OceanClient
from outreach.models.company import CompanyDomain
from outreach.models.contact import StageError
from outreach.stages.base import StageResult

logger = logging.getLogger(__name__)


class OceanStage:
    def __init__(self, client: OceanClient) -> None:
        self.client = client

    def run(self, seed_domain: str, max_companies: int) -> StageResult[CompanyDomain]:
        result = StageResult[CompanyDomain]()
        try:
            result.data = self.client.find_lookalikes(seed_domain, max_companies)
            logger.info("Ocean.io found %s lookalike companies", len(result.data))
        except Exception as exc:
            logger.exception("Ocean stage failed")
            result.errors.append(
                StageError(stage="ocean", message=str(exc), context={"seed": seed_domain})
            )
        return result
