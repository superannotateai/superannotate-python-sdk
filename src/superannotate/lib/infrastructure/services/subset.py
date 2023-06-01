from typing import List

from lib.core import entities
from lib.core.conditions import Condition
from lib.core.service_types import SubsetListResponse
from lib.core.serviceproviders import BaseSubsetService


class SubsetService(BaseSubsetService):
    URL_LIST = "/project/{project_id}/subset"
    URL_CREATE = "project/{project_id}/subset/bulk"
    URL_ADD_ITEMS_TO_SUBSET = "project/{project_id}/subset/{subset_id}/change"

    def list(self, project: entities.ProjectEntity, condition: Condition = None):
        url = self.URL_LIST.format(project_id=project.id)
        return self.client.paginate(
            url=f"{url}?{condition.build_query()}" if condition else url,
            item_type=entities.SubSetEntity,
        )

    def create_multiple(self, project: entities.ProjectEntity, name: List[str]):
        res = self.client.request(
            method="POST",
            url=self.URL_CREATE.format(project_id=project.id),
            data={"names": name},
            content_type=SubsetListResponse,
        )
        return res

    def add_items(
        self,
        project: entities.ProjectEntity,
        subset: entities.SubSetEntity,
        item_ids: List[int],
    ):
        data = {"action": "ATTACH", "item_ids": item_ids}
        response = self.client.request(
            url=self.URL_ADD_ITEMS_TO_SUBSET.format(
                project_id=project.id, subset_id=subset.id
            ),
            method="POST",
            data=data,
        )
        if not response.ok:
            response.res_data = {}
            response.res_data["skipped"] = set()
            response.res_data["failed"] = set(item_ids)
            response.res_data["success"] = set()
            return response

        response.data["skipped"] = set(response.data["skipped"])
        response.data["failed"] = set(response.data["failed"])
        response.data["success"] = set(item_ids) - response.data["skipped"].union(
            response.data["failed"]
        )
        return response
