import base64
import json
from typing import Dict
from typing import List
from urllib.parse import urljoin

import lib.core as constants
from lib.core import entities
from lib.core.conditions import Condition
from lib.core.service_types import ProjectResponse
from lib.core.service_types import ServiceResponse
from lib.core.service_types import SettingsListResponse
from lib.core.serviceproviders import BaseProjectService


class ProjectService(BaseProjectService):
    WORK_MANAGAMENT_VERSION = "v1"
    URL = "project"
    URL_LIST = "projects"
    URL_GET = "project/{}"
    URL_SETTINGS = "project/{}/settings"
    URL_WORKFLOW = "project/{}/workflow"
    URL_SHARE = "project/{}/share/bulk"
    URL_SHARE_PROJECT = "project/{}/share"
    URL_WORKFLOW_ATTRIBUTE = "project/{}/workflow_attribute"
    URL_UPLOAD_PRIORITY_SCORES = "images/updateEntropy"
    URL_ASSIGN_ITEMS = "images/editAssignment/"
    URL_GET_BY_ID = "project/{project_id}"
    URL_ATTACH_CATEGORIES = "items/bulk/setcategory"
    URL_LIST_CATEGORIES = "categories"
    URL_CREATE_CATEGORIES = "categories/bulk"

    @property
    def assets_work_management_url(self):
        if self.client.api_url != constants.BACKEND_URL:
            return f"https://work-management-api.devsuperannotate.com/api/{self.WORK_MANAGAMENT_VERSION}/"
        return f"https://work-management-api.superannotate.com/api/{self.WORK_MANAGAMENT_VERSION}/"

    def get_by_id(self, project_id: int):
        params = {}
        result = self.client.request(
            self.URL_GET_BY_ID.format(project_id=project_id),
            "get",
            params=params,
            content_type=ProjectResponse,
        )
        return result

    def get(self, uuid: int):
        return self.client.request(
            self.URL_GET.format(uuid), "get", content_type=ProjectResponse
        )

    def create(self, entity: entities.ProjectEntity) -> ServiceResponse:
        entity.team_id = self.client.team_id
        return self.client.request(
            self.URL, "post", data=entity, content_type=ProjectResponse
        )

    def list(self, condition: Condition = None):
        return self.client.paginate(
            url=self.URL_LIST,
            query_params=condition.get_as_params_dict(),
            item_type=entities.ProjectEntity,
        )

    def update(self, entity: entities.ProjectEntity):
        return self.client.request(
            self.URL_GET.format(entity.id),
            "put",
            data=entity,
            content_type=ProjectResponse,
        )

    def delete(self, entity: entities.ProjectEntity) -> ServiceResponse:
        return self.client.request(self.URL_GET.format(entity.id), "delete")

    def list_settings(self, project: entities.ProjectEntity):
        return self.client.request(
            self.URL_SETTINGS.format(project.id),
            "get",
            content_type=SettingsListResponse,
        )

    def set_settings(
        self, project: entities.ProjectEntity, data: List[entities.SettingEntity]
    ):
        return self.client.request(
            self.URL_SETTINGS.format(project.id),
            "put",
            data={"settings": data},
        )

    def share(self, project: entities.ProjectEntity, users: list):
        return self.client.request(
            self.URL_SHARE.format(project.id),
            "post",
            data={"users": users},
        )

    def list_workflows(self, project: entities.ProjectEntity):
        return self.client.paginate(
            self.URL_WORKFLOW.format(project.id), item_type=entities.WorkflowEntity
        )

    def set_workflow(
        self, project: entities.ProjectEntity, workflow: entities.WorkflowEntity
    ):
        return self.client.request(
            self.URL_WORKFLOW.format(project.id),
            "post",
            data={"steps": [workflow]},
        )

    # TODO check
    def set_workflows(self, project: entities.ProjectEntity, steps: list):
        return self.client.request(
            self.URL_WORKFLOW.format(project.id),
            "post",
            data={"steps": steps},
        )

    def set_project_workflow_attributes(
        self, project: entities.ProjectEntity, attributes: list
    ):
        return self.client.request(
            self.URL_WORKFLOW_ATTRIBUTE.format(project.id),
            "post",
            data={"data": attributes},
        )

    def un_share(self, project: entities.ProjectEntity, user_id: int):
        return self.client.request(
            self.URL_SHARE_PROJECT.format(project.id),
            "delete",
            data={"user_id": user_id},
        )

    def assign_items(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        user: str,
        item_names: List[str],
    ) -> ServiceResponse:
        return self.client.request(
            self.URL_ASSIGN_ITEMS,
            "put",
            params={"project_id": project.id},
            data={
                "image_names": item_names,
                "assign_user_id": user,
                "folder_name": folder.name,
            },
            content_type=ServiceResponse,
        )

    def un_assign_items(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        item_names: List[str],
    ) -> ServiceResponse:
        return self.client.request(
            self.URL_ASSIGN_ITEMS,
            "put",
            params={"project_id": project.id},
            data={
                "image_names": item_names,
                "remove_user_ids": ["all"],
                "folder_name": folder.name,
            },
        )

    def upload_priority_scores(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        priorities: list,
    ):
        return self.client.request(
            self.URL_UPLOAD_PRIORITY_SCORES,
            "post",
            params={
                "project_id": project.id,
                "folder_id": folder.id,
            },
            data={"image_entropies": priorities},
        )

    def get_entitiy_context(self, project_id: int):
        return base64.b64encode(
            json.dumps(
                {
                    "team_id": self.client.team_id,
                    "project_id": project_id,
                }
            ).encode()
        )

    def list_categories(
        self,
        project_id: int,
    ):
        params = [
            ("project_id", project_id),
        ]
        return self.client.request(
            urljoin(self.assets_work_management_url, self.URL_LIST_CATEGORIES),
            "get",
            params=params,
            headers={"x-sa-entity-context": self.get_entitiy_context(project_id)},
        )

    def create_categories(self, project_id: int, categories: List[str]):
        params = [
            ("project_id", project_id),
        ]
        res = self.client.request(
            urljoin(self.assets_work_management_url, self.URL_CREATE_CATEGORIES),
            "post",
            params=params,
            data={"bulk": [{"name": i} for i in categories]},
            headers={"x-sa-entity-context": self.get_entitiy_context(project_id)},
        )
        return res.data

    def attach_categories(
        self,
        project_id: int,
        folder_id: int,
        item_id_category_id_map: Dict[int, dict],
    ):
        params = [
            ("project_id", project_id),
            ("folder_id", folder_id),
        ]

        res = self.client.request(
            self.URL_ATTACH_CATEGORIES,
            "post",
            params=params,
            data={
                "bulk": [
                    {"item_id": item_id, "categories": [category]}
                    for item_id, category in item_id_category_id_map.items()
                ]
            },
        )
        return res
