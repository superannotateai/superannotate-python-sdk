import base64
from typing import Optional

from lib.core.entities import BaseItemEntity
from lib.core.jsx_conditions import Join
from lib.core.jsx_conditions import Query
from lib.core.service_types import BaseItemResponse
from lib.core.serviceproviders import SuperannotateServiceProvider


class ItemService(SuperannotateServiceProvider):
    URL_LIST = "items"
    URL_GET = "items/{item_id}"

    def get(self, project_id: int, item_id: int):
        result = self.client.request(
            url=self.URL_GET.format(item_id=item_id),
            method="GET",
            content_type=BaseItemResponse,
            headers={
                "x-sa-entity-context": base64.b64encode(
                    f'{{"team_id":{self.client.team_id},'
                    f'"project_id":{project_id}}}'.encode("utf-8")
                ).decode()
            },
        )
        return result

    def list(self, project_id: int, folder_id: Optional[int], query: Query):
        query &= Join("metadata", ["path"])
        entity_context = [
            f'"team_id":{self.client.team_id}',
            f'"project_id":{project_id}',
        ]
        if folder_id:
            entity_context.append(f'"folder_id":{folder_id}')
        result = self.client.paginate(
            f"{self.URL_LIST}?{query.build_query()}",
            item_type=BaseItemEntity,
            headers={
                "x-sa-entity-context": base64.b64encode(
                    f"{{{','.join(entity_context)}}}".encode("utf-8")
                ).decode()
            },
        )
        return result
