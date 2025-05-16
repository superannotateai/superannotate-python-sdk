from typing import List

from lib.core import entities
from lib.core.conditions import Condition
from lib.core.service_types import ProjectResponse
from lib.core.service_types import ServiceResponse
from lib.core.service_types import SettingsListResponse
from lib.core.serviceproviders import BaseProjectService


class ProjectService(BaseProjectService):
    URL = "project"
    URL_LIST = "api/v1/projects"
    URL_GET = "project/{}"
    URL_SETTINGS = "project/{}/settings"
    URL_STEPS = "project/{}/workflow"
    URL_KEYPOINT_STEPS = "api/v1/project/{}/downloadSteps"
    URL_SET_KEYPOINT_STEPS = "api/v1/project/{}/uploadSteps"
    URL_SHARE = "api/v1/project/{}/share/bulk"
    URL_SHARE_PROJECT = "project/{}/share"
    URL_STEP_ATTRIBUTE = "project/{}/workflow_attribute"
    URL_UPLOAD_PRIORITY_SCORES = "images/updateEntropy"
    URL_ASSIGN_ITEMS = "images/editAssignment/"
    URL_GET_BY_ID = "api/v1/project/{project_id}"
    URL_EDITOR_TEMPLATE = "/project/{project_id}/custom-editor-template"

    def get_by_id(self, project_id: int):
        params = {}
        result = self.client.request(
            self.URL_GET_BY_ID.format(project_id=project_id),
            "get",
            params=params,
            content_type=ProjectResponse,
        )
        return result

    def create(self, entity: entities.ProjectEntity) -> ServiceResponse:
        entity.team_id = self.client.team_id
        return self.client.request(
            self.URL, "post", data=entity, content_type=ProjectResponse
        )

    def attach_editor_template(
        self, team: entities.TeamEntity, project: entities.ProjectEntity, template: dict
    ) -> dict:
        url = self.URL_EDITOR_TEMPLATE.format(project_id=project.id)
        params = {
            "organization_id": team.owner_id,
        }
        return self.client.request(
            url, "post", data=template, content_type=ServiceResponse, params=params
        )

    def get_editor_template(self, organization_id: str, project_id: int) -> bool:
        url = self.URL_EDITOR_TEMPLATE.format(project_id=project_id)
        params = {
            "organization_id": organization_id,
        }
        return self.client.request(
            url, "get", content_type=ServiceResponse, params=params
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

    def list_steps(self, project: entities.ProjectEntity):
        return self.client.paginate(
            self.URL_STEPS.format(project.id), item_type=entities.StepEntity
        )

    def list_keypoint_steps(self, project: entities.ProjectEntity):
        return self.client.request(self.URL_KEYPOINT_STEPS.format(project.id), "get")

    def set_step(self, project: entities.ProjectEntity, step: entities.StepEntity):
        return self.client.request(
            self.URL_STEPS.format(project.id),
            "post",
            data={"steps": [step]},
        )

    def set_keypoint_steps(self, project: entities.ProjectEntity, steps, connections):
        return self.client.request(
            self.URL_SET_KEYPOINT_STEPS.format(project.id),
            "post",
            data={
                "steps": {
                    "steps": steps,
                    "connections": connections if connections else [],
                }
            },
        )

    # TODO check
    def set_steps(self, project: entities.ProjectEntity, steps: list):
        return self.client.request(
            self.URL_STEPS.format(project.id),
            "post",
            data={"steps": steps},
        )

    def set_project_step_attributes(
        self, project: entities.ProjectEntity, attributes: list
    ):
        return self.client.request(
            self.URL_STEP_ATTRIBUTE.format(project.id),
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
