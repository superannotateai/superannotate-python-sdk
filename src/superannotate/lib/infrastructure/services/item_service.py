import base64
from typing import Optional

from lib.core.entities import BaseItemEntity
from lib.core.jsx_conditions import Join
from lib.core.jsx_conditions import Query
from lib.core.service_types import BaseItemResponse
from lib.core.serviceproviders import SuperannotateServiceProvider
from superannotate import AppException


class ItemService(SuperannotateServiceProvider):
    MAX_URI_LENGTH = 15_000
    URL_LIST = "items/search"
    URL_GET = "items/{item_id}"

    def get(self, project_id: int, item_id: int, query: Query):
        result = self.client.request(
            url=f"{self.URL_GET.format(item_id=item_id)}?{query.build_query()}",
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

        response = self.client.jsx_paginate(
            url=self.URL_LIST,
            chunk_size=2000,
            body_query=query,
            method="post",
            item_type=BaseItemEntity,
            headers={
                "x-sa-entity-context": base64.b64encode(
                    f"{{{','.join(entity_context)}}}".encode("utf-8")
                ).decode()
            },
        )
        if not response.ok:
            raise AppException(response.error)
        return response.data
