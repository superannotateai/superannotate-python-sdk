from collections import ChainMap
from typing import Dict
from typing import List

from lib.core import entities
from lib.core.service_types import UploadCustomFieldValuesResponse
from lib.core.serviceproviders import BaseCustomFieldService


class CustomFieldService(BaseCustomFieldService):
    URL_CREATE_CUSTOM_SCHEMA = "/project/{project_id}/custom/metadata/schema"
    URL_UPLOAD_CUSTOM_VALUE = "/project/{project_id}/custom/metadata/item"

    def create_schema(self, project: entities.ProjectEntity, schema: dict):
        return self.client.request(
            self.URL_CREATE_CUSTOM_SCHEMA.format(project_id=project.id),
            "post",
            data=dict(data=schema),
        )

    def get_schema(self, project: entities.ProjectEntity):
        return self.client.request(
            self.URL_CREATE_CUSTOM_SCHEMA.format(project_id=project.id), "get"
        )

    def delete_fields(self, project: entities.ProjectEntity, fields: List[str]):
        return self.client.request(
            self.URL_CREATE_CUSTOM_SCHEMA.format(project_id=project.id),
            "delete",
            data=dict(custom_fields=fields),
        )

    def upload_fields(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        items: List[dict],
    ):
        return self.client.request(
            self.URL_UPLOAD_CUSTOM_VALUE.format(project_id=project.id),
            "post",
            params=dict(folder_id=folder.id),
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
            self.URL_UPLOAD_CUSTOM_VALUE.format(project_id=project.id),
            "delete",
            params=dict(folder_id=folder.id),
            data=dict(data=dict(ChainMap(*items))),
        )
