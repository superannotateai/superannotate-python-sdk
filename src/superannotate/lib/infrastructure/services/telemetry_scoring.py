from typing import List
from urllib.parse import urljoin

import lib.core as constants
from lib.core.entities.work_managament import TelemetryScoreEntity
from lib.core.service_types import ServiceResponse
from lib.core.service_types import TelemetryScoreListResponse
from lib.core.serviceproviders import BaseTelemetryScoringService


class TelemetryScoringService(BaseTelemetryScoringService):
    API_VERSION = "v1"

    URL_SCORES = "scores"

    @property
    def telemetry_service_url(self):
        if self.client.api_url != constants.BACKEND_URL:
            return f"https://telemetry-scoring.devsuperannotate.com/api/{self.API_VERSION}/"
        return f"https://telemetry-scoring.superannotate.com/api/{self.API_VERSION}/"

    def get_score_values(
        self,
        project_id: int,
        item_id: int,
        user_id: str,
    ) -> TelemetryScoreListResponse:
        query_params = {
            "team_id": self.client.team_id,
            "project_id": project_id,
            "item_id": item_id,
            "user_id": user_id,
        }
        return self.client.paginate(
            url=urljoin(self.telemetry_service_url, self.URL_SCORES),
            query_params=query_params,
            item_type=TelemetryScoreEntity,
        )

    def set_score_values(
        self,
        project_id: int,
        data: List[dict],
    ) -> ServiceResponse:
        params = {
            "project_id": project_id,
        }
        return self.client.request(
            url=urljoin(self.telemetry_service_url, self.URL_SCORES),
            method="post",
            params=params,
            data={"data": data},
        )
