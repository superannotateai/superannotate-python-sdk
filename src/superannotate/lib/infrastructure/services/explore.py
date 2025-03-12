from collections import ChainMap
from typing import Dict
from typing import List
from urllib.parse import urljoin

import lib.core as constants
from lib.core import entities
from lib.core.conditions import Condition
from lib.core.service_types import ServiceResponse
from lib.core.service_types import SubsetListResponse
from lib.core.service_types import UploadCustomFieldValuesResponse
from lib.core.serviceproviders import BaseExploreService
from superannotate import AppException


class ExploreService(BaseExploreService):
    API_VERSION = "v1"
    MAX_ITEMS_COUNT = 50_1000
    CHUNK_SIZE = 5_000
    SAQUL_CHUNK_SIZE = 50

    URL_SUBSET = "subsets"
    URL_LIST_CUSTOM_FIELDS = "custom/metadata/item/value"
    URL_ADD_ITEMS_TO_SUBSET = "subsets/change"
    URL_CUSTOM_SCHEMA = "custom/metadata/schema"
    URL_UPLOAD_CUSTOM_VALUE = "custom/metadata/item"
    URL_SAQUL_QUERY = "items/search"
    URL_VALIDATE_SAQUL_QUERY = "items/parse/query"
    URL_QUERY_COUNT = "items/count"

    @property
    def explore_service_url(self):
        if self.client.api_url != constants.BACKEND_URL:
            return (
                f"http://explore-service.devsuperannotate.com/api/{self.API_VERSION}/"
            )
        return f"https://explore-service.superannotate.com/api/{self.API_VERSION}/"

    def create_schema(self, project: entities.ProjectEntity, schema: dict):
        return self.client.request(
            url=urljoin(self.explore_service_url, self.URL_CUSTOM_SCHEMA),
            method="post",
            params={"project_id": project.id},
            data=dict(data=schema),
        )

    def get_schema(self, project: entities.ProjectEntity):
        return self.client.request(
            url=urljoin(self.explore_service_url, self.URL_CUSTOM_SCHEMA),
            method="get",
            params={"project_id": project.id},
        )

    def delete_fields(self, project: entities.ProjectEntity, fields: List[str]):
        return self.client.request(
            url=urljoin(self.explore_service_url, self.URL_CUSTOM_SCHEMA),
            method="delete",
            params={"project_id": project.id},
            data=dict(custom_fields=fields),
        )

    def upload_fields(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        items: List[dict],
    ):
        return self.client.request(
            url=urljoin(self.explore_service_url, self.URL_UPLOAD_CUSTOM_VALUE),
            method="post",
            params={"project_id": project.id, "folder_id": folder.id},
            data=dict(data=dict(ChainMap(*items))),
            content_type=UploadCustomFieldValuesResponse,
        )

    def delete_values(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        items: List[Dict[str, List[str]]],
    ):
        return self.client.request(
            url=urljoin(self.explore_service_url, self.URL_UPLOAD_CUSTOM_VALUE),
            method="delete",
            params={"project_id": project.id, "folder_id": folder.id},
            data=dict(data=dict(ChainMap(*items))),
        )

    def list_fields(self, project: entities.ProjectEntity, item_ids: List[int]):
        assert len(item_ids) <= self.CHUNK_SIZE
        return self.client.request(
            url=urljoin(self.explore_service_url, self.URL_LIST_CUSTOM_FIELDS),
            method="POST",
            params={"project_id": project.id},
            data={
                "item_id": item_ids,
            },
        )

    def list_subsets(
        self, project: entities.ProjectEntity, condition: Condition = None
    ):
        url = urljoin(self.explore_service_url, self.URL_SUBSET)
        return self.client.paginate(
            url=f"{url}?{condition.build_query()}" if condition else url,
            query_params={"project_id": project.id},
            item_type=entities.SubSetEntity,
        )

    def create_multiple_subsets(self, project: entities.ProjectEntity, name: List[str]):
        res = self.client.request(
            method="POST",
            url=urljoin(self.explore_service_url, self.URL_SUBSET),
            params={"project_id": project.id},
            data={"names": name},
            content_type=SubsetListResponse,
        )
        return res

    def add_items_to_subset(
        self,
        project: entities.ProjectEntity,
        subset: entities.SubSetEntity,
        item_ids: List[int],
    ):
        data = {"action": "ATTACH", "item_ids": item_ids}
        response = self.client.request(
            url=urljoin(self.explore_service_url, self.URL_ADD_ITEMS_TO_SUBSET),
            method="POST",
            params={"project_id": project.id, "subset_id": subset.id},
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

    def validate_saqul_query(self, project: entities.ProjectEntity, query: str):
        params = {
            "project_id": project.id,
        }
        data = {
            "query": query,
        }
        return self.client.request(
            urljoin(self.explore_service_url, self.URL_VALIDATE_SAQUL_QUERY),
            "post",
            params=params,
            data=data,
        )

    def saqul_query(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity = None,
        query: str = None,
        subset_id: int = None,
    ) -> ServiceResponse:

        params = {
            "project_id": project.id,
            "includeFolderNames": True,
        }
        if folder:
            params["folder_id"] = folder.id
        if subset_id:
            params["subset_id"] = subset_id
        data = {"image_index": 0}
        if query:
            data["query"] = query
        items = []
        response = None
        for _ in range(0, self.MAX_ITEMS_COUNT, self.SAQUL_CHUNK_SIZE):
            response = self.client.request(
                urljoin(self.explore_service_url, self.URL_SAQUL_QUERY),
                "post",
                params=params,
                data=data,
            )
            if not response.ok:
                break
            response_items = response.data
            items.extend(response_items)
            if len(response_items) < self.SAQUL_CHUNK_SIZE:
                break
            data["image_index"] += self.SAQUL_CHUNK_SIZE

        if response:
            response = ServiceResponse(status=response.status_code, res_data=items)
            if not response.ok:
                response.set_error(response.error)
                response = ServiceResponse(status=response.status_code, res_data=items)
        else:
            response = ServiceResponse(status=200, res_data=[])
        return response

    def query_item_count(
        self,
        project: entities.ProjectEntity,
        query: str = None,
    ) -> ServiceResponse:

        params = {
            "project_id": project.id,
            "includeFolderNames": True,
        }
        data = {"query": query}
        response = self.client.request(
            urljoin(self.explore_service_url, self.URL_QUERY_COUNT),
            "post",
            params=params,
            data=data,
        )
        if not response.ok:
            raise AppException(response.error)
        return response
