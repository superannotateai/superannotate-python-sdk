import lib.core as constants
from lib.core.jsx_conditions import Query
from lib.core.service_types import WorkflowListResponse
from lib.core.serviceproviders import SuperannotateServiceProvider


class WorkManagamentService(SuperannotateServiceProvider):
    API_VERSION = "v1"
    URL_GET = "workflows/{project_id}"
    URL_LIST = "workflows"

    def _get_url(self):
        if self.client.api_url != constants.BACKEND_URL:
            return f"https://work-management-api.devsuperannotate.com/api/{self.API_VERSION}/"
        return (
            f"https://work-management-api.devsuperannotate.com/api/{self.API_VERSION}/"
        )

    def list(self, query: Query):
        result = self.client.request(
            f"{self.URL_LIST}/{query.build_query()}",
            "get",
            content_type=WorkflowListResponse,
        )
        return result
