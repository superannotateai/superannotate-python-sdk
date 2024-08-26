import lib.core as constants
from lib.core.jsx_conditions import Query
from lib.core.service_types import ItemListResponse
from lib.core.serviceproviders import SuperannotateServiceProvider


class ItemService(SuperannotateServiceProvider):
    URL_LIST = "items"

    def list(self, query: Query):
        result = self.client.request(
            f"{self.URL_LIST}/{query.build_query()}",
            "get",
            content_type=ItemListResponse,
        )
        return result
