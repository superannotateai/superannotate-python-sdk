from typing import List

from lib.core import entities
from lib.core.conditions import Condition
from lib.core.service_types import FolderResponse
from lib.core.serviceproviders import BaseFolderService


class FolderService(BaseFolderService):
    URL_BASE = "folder"
    URL_LIST = "folders"
    URL_GET_BY_NAME = "folder/getFolderByName"
    URL_DELETE_MULTIPLE = "image/delete/images"

    def get_by_name(self, project: entities.ProjectEntity, name: str):
        params = {"project_id": project.id, "name": name}
        return self.client.request(
            self.URL_GET_BY_NAME, "get", params=params, content_type=FolderResponse
        )

    def create(self, project: entities.ProjectEntity, folder: entities.FolderEntity):
        data = {"name": folder.name}
        params = {"project_id": project.id}
        return self.client.request(
            self.URL_BASE, "post", data=data, params=params, content_type=FolderResponse
        )

    def list(self, condition: Condition = None):
        return self.client.paginate(
            url=f"{self.URL_LIST}?{condition.build_query()}"
            if condition
            else self.URL_LIST,
            item_type=entities.FolderEntity,
        )

    def delete_multiple(
        self, project: entities.ProjectEntity, folders: List[entities.FolderEntity]
    ):
        params = {"project_id": project.id}
        return self.client.request(
            self.URL_DELETE_MULTIPLE,
            "put",
            params=params,
            data={"folder_ids": [i.id for i in folders]},
        )
