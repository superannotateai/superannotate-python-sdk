import lib.core as constants
from lib.core.jsx_conditions import Query
from lib.core.service_types import WorkflowListResponse
from lib.core.serviceproviders import SuperannotateServiceProvider


class WorkManagamentService(SuperannotateServiceProvider):
    URL_GET = "workflows/{project_id}"
    URL_LIST = "workflows"

    def list(self, query: Query):
        result = self.client.request(
            f"{self.URL_LIST}/{query.build_query()}",
            "get",
            content_type=WorkflowListResponse,
        )
        return result