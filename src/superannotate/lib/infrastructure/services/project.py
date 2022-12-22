from typing import List

from lib.core import entities
from lib.core.conditions import Condition
from lib.core.service_types import ProjectResponse
from lib.core.service_types import ServiceResponse
from lib.core.service_types import SettingsListResponse
from lib.core.serviceproviders import BaseProjectService


class ProjectService(BaseProjectService):
    URL = "project"
    URL_LIST = "projects"
    URL_GET = "project/{}"
    URL_SETTINGS = "project/{}/settings"
    URL_SHARE = "project/{}/share/bulk"
    URL_WORKFLOW = "project/{}/workflow"
    URL_SHARE_PROJECT = "project/{}/share"
    URL_WORKFLOW_ATTRIBUTE = "project/{}/workflow_attribute"
    URL_UPLOAD_PRIORITY_SCORES = "images/updateEntropy"
    URL_ASSIGN_ITEMS = "images/editAssignment/"
    URL_GET_BY_ID = "project/{project_id}"

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
            url=f"{self.URL_LIST}?{condition.build_query()}"
            if condition
            else self.URL_LIST,
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
