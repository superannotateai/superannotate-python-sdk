import base64
import datetime
from typing import List

import lib.core as constants
from lib.core import entities
from lib.core.conditions import Condition
from lib.core.enums import ApprovalStatus
from lib.core.enums import CustomFieldEntityEnum
from lib.core.service_types import TeamResponse
from lib.core.service_types import UploadAnnotationAuthDataResponse
from lib.core.service_types import UserLimitsResponse
from lib.core.service_types import UserResponse
from lib.core.serviceproviders import BaseServiceProvider
from lib.infrastructure.services.annotation import AnnotationService
from lib.infrastructure.services.annotation_class import AnnotationClassService
from lib.infrastructure.services.explore import ExploreService
from lib.infrastructure.services.folder import FolderService
from lib.infrastructure.services.http_client import HttpClient
from lib.infrastructure.services.integration import IntegrationService
from lib.infrastructure.services.item import ItemService
from lib.infrastructure.services.item_service import ItemService as SeparateItemService
from lib.infrastructure.services.project import ProjectService
from lib.infrastructure.services.telemetry_scoring import TelemetryScoringService
from lib.infrastructure.services.work_management import WorkManagementService
from lib.infrastructure.utils import CachedWorkManagementRepository
from lib.infrastructure.utils import EntityContext


class ServiceProvider(BaseServiceProvider):
    URL_TEAM = "api/v1/team"
    URL_GET_LIMITS = "project/{project_id}/limitationDetails"
    URL_GET_TEMPLATES = "templates"
    URL_PREPARE_EXPORT = "export"
    URL_GET_EXPORTS = "exports"
    URL_USER = "user/ME"
    URL_USERS = "users"
    URL_GET_EXPORT = "export/{}"
    URL_PREDICTION = "images/prediction"
    URL_FOLDERS_IMAGES = "images-folders"
    URL_INVITE_CONTRIBUTORS = "api/v1/team/{}/inviteUsers"
    URL_ANNOTATION_UPLOAD_PATH_TOKEN = "images/getAnnotationsPathsAndTokens"
    URL_CREATE_WORKFLOW = "api/v1/workflows/submit"

    def __init__(self, client: HttpClient):
        self.enum_mapping = {"approval_status": ApprovalStatus.get_mapping()}

        self.client = client
        self.projects = ProjectService(client)
        self.folders = FolderService(client)
        self.items = ItemService(client)
        self.annotations = AnnotationService(client)
        self.annotation_classes = AnnotationClassService(client)
        self.integrations = IntegrationService(client)
        self.explore = ExploreService(client)
        self.telemetry_scoring = TelemetryScoringService(client)
        self.work_management = WorkManagementService(
            HttpClient(
                api_url=self._get_work_management_url(client),
                token=client.token,
                verify_ssl=client.verify_ssl,
            )
        )
        self.item_service = SeparateItemService(
            HttpClient(
                api_url=self._get_item_service_url(client),
                token=client.token,
                verify_ssl=client.verify_ssl,
            )
        )
        self._cached_work_management_repository = CachedWorkManagementRepository(
            5, self.work_management
        )

    def get_custom_fields_templates(
        self,
        context: EntityContext,
        entity: CustomFieldEntityEnum,
        parent: CustomFieldEntityEnum,
    ):
        return self._cached_work_management_repository.list_templates(
            context, entity=entity, parent=parent
        )

    def list_custom_field_names(
        self,
        context: EntityContext,
        entity: CustomFieldEntityEnum,
        parent: CustomFieldEntityEnum,
    ) -> List[str]:
        return self._cached_work_management_repository.list_custom_field_names(
            context,
            entity=entity,
            parent=parent,
        )

    def get_category_id(
        self, project: entities.ProjectEntity, category_name: str
    ) -> int:
        return self._cached_work_management_repository.get_category_id(
            project, category_name
        )

    def get_custom_field_id(
        self,
        context: EntityContext,
        field_name: str,
        entity: CustomFieldEntityEnum,
        parent: CustomFieldEntityEnum,
    ) -> int:
        return self._cached_work_management_repository.get_custom_field_id(
            context, field_name, entity=entity, parent=parent
        )

    def get_custom_field_name(
        self,
        context: EntityContext,
        field_id: int,
        entity: CustomFieldEntityEnum,
        parent: CustomFieldEntityEnum,
    ) -> str:
        return self._cached_work_management_repository.get_custom_field_name(
            context, field_id, entity=entity, parent=parent
        )

    def get_custom_field_component_id(
        self,
        context: EntityContext,
        field_id: int,
        entity: CustomFieldEntityEnum,
        parent: CustomFieldEntityEnum,
    ) -> str:
        return self._cached_work_management_repository.get_custom_field_component_id(
            context, field_id, entity=entity, parent=parent
        )

    def get_role_id(self, project: entities.ProjectEntity, role_name: str) -> int:
        return self._cached_work_management_repository.get_role_id(project, role_name)

    def get_role_name(self, project: entities.ProjectEntity, role_id: int) -> str:
        return self._cached_work_management_repository.get_role_name(project, role_id)

    def get_annotation_status_value(
        self, project: entities.ProjectEntity, status_name: str
    ) -> int:
        return self._cached_work_management_repository.get_annotation_status_value(
            project, status_name
        )

    def get_annotation_status_name(
        self, project: entities.ProjectEntity, status_value: int
    ) -> str:
        return self._cached_work_management_repository.get_annotation_status_name(
            project, status_value
        )

    @staticmethod
    def _get_work_management_url(client: HttpClient):
        if client.api_url != constants.BACKEND_URL:
            return "https://work-management-api.devsuperannotate.com/api/v1/"
        return "https://work-management-api.superannotate.com/api/v1/"

    @staticmethod
    def _get_item_service_url(client: HttpClient):
        if client.api_url != constants.BACKEND_URL:
            return "https://item.devsuperannotate.com/api/v1/"
        return "https://item.superannotate.com/api/v1/"

    def get_team(self, team_id: int) -> TeamResponse:
        return self.client.request(
            f"{self.URL_TEAM}/{team_id}", "get", content_type=TeamResponse
        )

    def get_user(self, team_id: int) -> UserResponse:
        return self.client.request(
            self.URL_USER, "get", params={"team_id": team_id}, content_type=UserResponse
        )

    def list_templates(self):
        return self.client.request(self.URL_GET_TEMPLATES, "get")

    def get_limitations(
        self, project: entities.ProjectEntity, folder: entities.FolderEntity
    ):
        return self.client.request(
            self.URL_GET_LIMITS.format(project_id=project.id),
            "get",
            params={"folder_id": folder.id},
            content_type=UserLimitsResponse,
        )

    def get_download_token(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        image_id: int,
        include_original: int = 1,
    ):

        download_token_url = (
            f"image/{image_id}" + "/annotation/getAnnotationDownloadToken"
        )
        return self.client.request(
            download_token_url,
            "get",
            params={
                "project_id": project.id,
                "folder_id": folder.id,
                "include_original": include_original,
            },
        )

    def get_upload_token(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        image_id: int,
    ):
        download_token_url = (
            f"image/{image_id}" + "/annotation/getAnnotationUploadToken"
        )
        return self.client.request(
            download_token_url,
            "get",
            params={
                "project_id": project.id,
                "folder_id": folder.id,
            },
        )

    def get_s3_upload_auth_token(
        self, project: entities.ProjectEntity, folder: entities.FolderEntity
    ):
        auth_token_url = f"project/{project.id}" + "/sdkImageUploadToken"
        return self.client.request(
            auth_token_url, "get", params={"folder_id": folder.id}
        )

    def get_annotation_upload_data(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        item_ids: List[int],
    ):
        return self.client.request(
            self.URL_ANNOTATION_UPLOAD_PATH_TOKEN,
            "post",
            data={
                "project_id": project.id,
                "team_id": project.team_id,
                "ids": item_ids,
                "folder_id": folder.id,
            },
            content_type=UploadAnnotationAuthDataResponse,
        )

    def prepare_export(
        self,
        project: entities.ProjectEntity,
        folders: List[str],
        include_fuse: bool,
        only_pinned: bool,
        annotation_statuses: List[str] = None,
        integration_id: int = None,
        export_type: int = None,
    ):

        data = {
            "fuse": int(include_fuse),
            "is_pinned": int(only_pinned),
            "coco": 0,
            "time": datetime.datetime.now().strftime("%b %d %Y %H:%M"),
        }
        if annotation_statuses:
            data["include"] = ",".join(
                [
                    str(self.get_annotation_status_value(project, i))
                    for i in annotation_statuses
                ]
            )
        if export_type:
            data["export_format"] = export_type
        if folders:
            data["folder_names"] = folders
        if integration_id is not None:
            data["integration_id"] = integration_id
        return self.client.request(
            self.URL_PREPARE_EXPORT,
            "post",
            data=data,
            params={"project_id": project.id},
        )

    def get_exports(self, project: entities.ProjectEntity):
        return self.client.request(
            self.URL_GET_EXPORTS, "get", params={"project_id": project.id}
        )

    def get_export(self, project: entities.ProjectEntity, export_id: int):
        return self.client.request(
            self.URL_GET_EXPORT.format(export_id),
            "get",
            params={"project_id": project.id},
        )

    def get_project_images_count(self, project: entities.ProjectEntity):
        return self.client.request(
            self.URL_FOLDERS_IMAGES,
            "get",
            params={"project_id": project.id},
        )

    def search_team_contributors(self, condition: Condition = None):
        list_users_url = self.URL_USERS
        if condition:
            list_users_url = f"{list_users_url}?{condition.build_query()}"
        return self.client.paginate(list_users_url)

    def invite_contributors(self, team_id: int, team_role: int, emails: List[str]):
        return self.client.request(
            self.URL_INVITE_CONTRIBUTORS.format(team_id),
            "post",
            data=dict(emails=emails, team_role=team_role),
        )

    def create_custom_workflow(self, org_id: str, data: dict):
        return self.client.request(
            url=self.URL_CREATE_WORKFLOW,
            method="post",
            headers={
                "x-sa-entity-context": base64.b64encode(
                    f'{{"team_id":{self.client.team_id},"organization_id":"{org_id}"}}'.encode(
                        "utf-8"
                    )
                ).decode()
            },
            data=data,
        )
