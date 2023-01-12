import datetime
from typing import List

import lib.core as constants
from lib.core import entities
from lib.core.conditions import Condition
from lib.core.service_types import DownloadMLModelAuthDataResponse
from lib.core.service_types import ServiceResponse
from lib.core.service_types import TeamResponse
from lib.core.service_types import UploadAnnotationAuthDataResponse
from lib.core.service_types import UserLimitsResponse
from lib.core.serviceproviders import BaseServiceProvider
from lib.infrastructure.services.annotation import AnnotationService
from lib.infrastructure.services.annotation_class import AnnotationClassService
from lib.infrastructure.services.custom_field import CustomFieldService
from lib.infrastructure.services.folder import FolderService
from lib.infrastructure.services.http_client import HttpClient
from lib.infrastructure.services.integration import IntegrationService
from lib.infrastructure.services.item import ItemService
from lib.infrastructure.services.models import ModelsService
from lib.infrastructure.services.project import ProjectService
from lib.infrastructure.services.subset import SubsetService


class ServiceProvider(BaseServiceProvider):
    MAX_ITEMS_COUNT = 50 * 1000
    SAQUL_CHUNK_SIZE = 50

    URL_TEAM = "team"
    URL_GET_LIMITS = "project/{project_id}/limitationDetails"
    URL_GET_TEMPLATES = "templates"
    URL_PREPARE_EXPORT = "export"
    URL_GET_EXPORTS = "exports"
    URL_USERS = "users"
    URL_GET_EXPORT = "export/{}"
    URL_GET_MODEL_METRICS = "ml_models/{}/getCurrentMetrics"
    URL_PREDICTION = "images/prediction"
    URL_SAQUL_QUERY = "/images/search/advanced"
    URL_FOLDERS_IMAGES = "images-folders"
    URL_INVITE_CONTRIBUTORS = "team/{}/inviteUsers"
    URL_VALIDATE_SAQUL_QUERY = "/images/parse/query/advanced"
    URL_GET_ML_MODEL_DOWNLOAD_TOKEN = "ml_model/getMyModelDownloadToken/{}"
    URL_ANNOTATION_UPLOAD_PATH_TOKEN = "images/getAnnotationsPathsAndTokens"

    def __init__(self, client: HttpClient):
        self.client = client
        self.projects = ProjectService(client)
        self.folders = FolderService(client)
        self.items = ItemService(client)
        self.annotations = AnnotationService(client)
        self.annotation_classes = AnnotationClassService(client)
        self.custom_fields = CustomFieldService(client)
        self.subsets = SubsetService(client)
        self.models = ModelsService(client)
        self.integrations = IntegrationService(client)

    def get_team(self, team_id: int) -> TeamResponse:
        return self.client.request(
            f"{self.URL_TEAM}/{team_id}", "get", content_type=TeamResponse
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
        annotation_statuses: List[str],
        include_fuse: bool,
        only_pinned: bool,
    ):
        annotation_statuses = ",".join(
            [str(constants.AnnotationStatus.get_value(i)) for i in annotation_statuses]
        )

        data = {
            "include": annotation_statuses,
            "fuse": int(include_fuse),
            "is_pinned": int(only_pinned),
            "coco": 0,
            "time": datetime.datetime.now().strftime("%b %d %Y %H:%M"),
        }
        if folders:
            data["folder_names"] = folders

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

    def get_model_metrics(self, model_id: int):
        return self.client.request(self.URL_GET_MODEL_METRICS.format(model_id), "get")

    def get_export(self, project: entities.ProjectEntity, export_id: int):
        return self.client.request(
            self.URL_GET_EXPORT.format(export_id),
            "get",
            params={"project_id": project.id},
        )

    def get_ml_model_download_tokens(self, model_id: int):
        return self.client.request(
            self.URL_GET_ML_MODEL_DOWNLOAD_TOKEN.format(model_id),
            "get",
            content_type=DownloadMLModelAuthDataResponse,
        )

    def run_prediction(
        self, project: entities.ProjectEntity, ml_model_id: int, image_ids: list
    ):
        return self.client.request(
            self.URL_PREDICTION,
            "post",
            data={
                "project_id": project.id,
                "ml_model_id": ml_model_id,
                "image_ids": image_ids,
            },
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

    def validate_saqul_query(self, project: entities.ProjectEntity, query: str):
        params = {
            "project_id": project.id,
        }
        data = {
            "query": query,
        }
        return self.client.request(
            self.URL_VALIDATE_SAQUL_QUERY, "post", params=params, data=data
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
                self.URL_SAQUL_QUERY, "post", params=params, data=data
            )
            if not response.ok:
                break
            response_items = response.data
            items.extend(response_items)
            if len(response_items) < self.SAQUL_CHUNK_SIZE:
                break
            data["image_index"] += self.SAQUL_CHUNK_SIZE

        if response:
            response = ServiceResponse(status=response.status_code, data=items)
            if not response.ok:
                response.set_error(response.error)
                response = ServiceResponse(status=response.status_code, data=items)
        else:
            response = ServiceResponse(status=200, data=[])
        return response
