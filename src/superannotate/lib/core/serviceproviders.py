import io
from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import Callable
from typing import Dict
from typing import List

from lib.core import entities
from lib.core.conditions import Condition
from lib.core.reporter import Reporter
from lib.core.service_types import AnnotationClassListResponse
from lib.core.service_types import DownloadMLModelAuthDataResponse
from lib.core.service_types import FolderListResponse
from lib.core.service_types import FolderResponse
from lib.core.service_types import IntegrationListResponse
from lib.core.service_types import ItemListResponse
from lib.core.service_types import ModelListResponse
from lib.core.service_types import ProjectListResponse
from lib.core.service_types import ProjectResponse
from lib.core.service_types import ServiceResponse
from lib.core.service_types import SettingsListResponse
from lib.core.service_types import SubsetListResponse
from lib.core.service_types import TeamResponse
from lib.core.service_types import UploadAnnotationAuthDataResponse
from lib.core.service_types import UploadAnnotationsResponse
from lib.core.service_types import UploadCustomFieldValuesResponse
from lib.core.service_types import UserLimitsResponse
from lib.core.service_types import UserResponse
from lib.core.types import Attachment
from lib.core.types import AttachmentMeta


class BaseClient(ABC):
    def __init__(self, api_url: str, token: str):
        self.team_id = token.split("=")[-1]

        self._api_url = api_url
        self._token = token

    @property
    def api_url(self):
        return self._api_url

    @property
    @abstractmethod
    def default_headers(self):
        raise NotImplementedError

    @abstractmethod
    def request(self, method: str, url: str, **kwargs) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def paginate(
        self,
        url: str,
        item_type: Any,
        chunk_size: int = 2000,
        query_params: Dict[str, Any] = None,
    ) -> ServiceResponse:
        raise NotImplementedError


class SuperannotateServiceProvider(ABC):
    def __init__(self, client: BaseClient):
        self.client = client


class BaseProjectService(SuperannotateServiceProvider):
    @abstractmethod
    def get(self, uuid: int):
        raise NotImplementedError

    @abstractmethod
    def create(self, entity: entities.ProjectEntity) -> ProjectResponse:
        raise NotImplementedError

    @abstractmethod
    def list(self, condition: Condition = None) -> ProjectListResponse:
        raise NotImplementedError

    @abstractmethod
    def update(self, entity: entities.ProjectEntity) -> ProjectResponse:
        raise NotImplementedError

    @abstractmethod
    def delete(self, entity: entities.ProjectEntity) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def list_settings(self, project: entities.ProjectEntity) -> SettingsListResponse:
        raise NotImplementedError

    @abstractmethod
    def set_settings(
        self, project: entities.ProjectEntity, data: List[entities.SettingEntity]
    ):
        raise NotImplementedError

    @abstractmethod
    def list_workflows(self, project: entities.ProjectEntity):
        raise NotImplementedError

    @abstractmethod
    def set_workflow(
        self, project: entities.ProjectEntity, workflow: entities.WorkflowEntity
    ):
        raise NotImplementedError

    @abstractmethod
    def set_workflows(self, project: entities.ProjectEntity, steps: list):
        raise NotImplementedError

    @abstractmethod
    def share(self, project: entities.ProjectEntity, users: list) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def un_share(self, project: entities.ProjectEntity, user_id) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def set_project_workflow_attributes(
        self, project: entities.ProjectEntity, attributes: list
    ):
        raise NotImplementedError

    @abstractmethod
    def assign_items(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        user: str,
        item_names: List[str],
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def un_assign_items(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        item_names: List[str],
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def upload_priority_scores(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        priorities: list,
    ) -> ServiceResponse:
        raise NotImplementedError


class BaseFolderService(SuperannotateServiceProvider):
    @abstractmethod
    def get_by_id(self, folder_id: int, project_id: int, team_id: int):
        raise NotImplementedError

    @abstractmethod
    def get_by_name(self, project: entities.ProjectEntity, name: str) -> FolderResponse:
        raise NotImplementedError

    @abstractmethod
    def create(
        self, project: entities.ProjectEntity, folder: entities.FolderEntity
    ) -> FolderResponse:
        raise NotImplementedError

    @abstractmethod
    def list(self, condition: Condition = None) -> FolderListResponse:
        raise NotImplementedError

    @abstractmethod
    def delete_multiple(
        self, project: entities.ProjectEntity, folders: List[entities.FolderEntity]
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def un_assign_all(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def assign(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        users: list,
    ):
        raise NotImplementedError

    @abstractmethod
    def update(
        self, project: entities.ProjectEntity, folder: entities.FolderEntity
    ) -> ServiceResponse:
        raise NotImplementedError


class BaseAnnotationClassService(SuperannotateServiceProvider):
    @abstractmethod
    def create_multiple(
        self,
        project: entities.ProjectEntity,
        classes: List[entities.AnnotationClassEntity],
    ) -> AnnotationClassListResponse:
        raise NotImplementedError

    @abstractmethod
    def list(self, condition: Condition = None) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def create(
        self, project_id: int, item: entities.AnnotationClassEntity
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def delete(self, project_id: int, annotation_class_id: int) -> ServiceResponse:
        raise NotImplementedError


class BaseItemService(SuperannotateServiceProvider):
    @abstractmethod
    def list(self, condition: Condition = None) -> ItemListResponse:
        raise NotImplementedError

    @abstractmethod
    def update(self, project: entities.ProjectEntity, item: entities.BaseItemEntity):
        raise NotImplementedError

    @abstractmethod
    def list_by_names(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        names: List[str],
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def list_by_ids(
        self,
        project: entities.ProjectEntity,
        ids: List[int],
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def attach(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        attachments: List[Attachment],
        annotation_status_code,
        upload_state_code,
        meta: Dict[str, AttachmentMeta],
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def move_multiple(
        self,
        project: entities.ProjectEntity,
        from_folder: entities.FolderEntity,
        to_folder: entities.FolderEntity,
        item_names: List[str],
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def copy_multiple(
        self,
        project: entities.ProjectEntity,
        from_folder: entities.FolderEntity,
        to_folder: entities.FolderEntity,
        item_names: List[str],
        include_annotations: bool = False,
        include_pin: bool = False,
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def await_copy(self, project: entities.ProjectEntity, poll_id: int, items_count):
        raise NotImplementedError

    @abstractmethod
    def set_statuses(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        item_names: List[str],
        annotation_status: int,
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def set_approval_statuses(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        item_names: List[str],
        approval_status: int,
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def delete_multiple(
        self, project: entities.ProjectEntity, item_ids: List[int]
    ) -> ServiceResponse:
        raise NotImplementedError


class BaseAnnotationService(SuperannotateServiceProvider):
    @abstractmethod
    async def get_big_annotation(
        self,
        project: entities.ProjectEntity,
        item: entities.BaseItemEntity,
        reporter: Reporter,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    async def list_small_annotations(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        item_ids: List[int],
        reporter: Reporter,
        callback: Callable = None,
    ) -> List[dict]:
        raise NotImplementedError

    @abstractmethod
    def get_upload_chunks(
        self,
        project: entities.ProjectEntity,
        item_ids: List[int],
    ) -> Dict[str, List]:
        raise NotImplementedError

    @abstractmethod
    async def download_big_annotation(
        self,
        project: entities.ProjectEntity,
        download_path: str,
        item: entities.BaseItemEntity,
        callback: Callable = None,
    ):
        raise NotImplementedError

    @abstractmethod
    async def download_small_annotations(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        reporter: Reporter,
        download_path: str,
        item_ids: List[int],
        callback: Callable = None,
    ):
        raise NotImplementedError

    @abstractmethod
    async def upload_small_annotations(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        items_name_data_map: Dict[str, dict],
    ) -> UploadAnnotationsResponse:
        raise NotImplementedError

    @abstractmethod
    async def upload_big_annotation(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        item_id: int,
        data: io.StringIO,
        chunk_size: int,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    def delete(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity = None,
        item_names: List[str] = None,
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def get_delete_progress(
        self, project: entities.ProjectEntity, poll_id: int
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def get_schema(self, project_type: int, version: str) -> ServiceResponse:
        raise NotImplementedError


class BaseCustomFieldService(SuperannotateServiceProvider):
    @abstractmethod
    def create_schema(
        self, project: entities.ProjectEntity, schema: dict
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def get_schema(self, project: entities.ProjectEntity) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def delete_fields(
        self, project: entities.ProjectEntity, fields: List[str]
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def upload_fields(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        items: List[dict],
    ) -> UploadCustomFieldValuesResponse:
        raise NotImplementedError

    @abstractmethod
    def delete_values(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        items: List[Dict[str, List[str]]],
    ) -> ServiceResponse:
        raise NotImplementedError


class BaseSubsetService(SuperannotateServiceProvider):
    @abstractmethod
    def list(
        self, project: entities.ProjectEntity, condition: Condition = None
    ) -> SubsetListResponse:
        raise NotImplementedError

    @abstractmethod
    def create_multiple(
        self, project: entities.ProjectEntity, names: List[str]
    ) -> SubsetListResponse:
        raise NotImplementedError

    @abstractmethod
    def add_items(
        self,
        project: entities.ProjectEntity,
        subset: entities.SubSetEntity,
        item_ids: List[int],
    ) -> ServiceResponse:
        raise NotImplementedError


class BaseModelsService(SuperannotateServiceProvider):
    @abstractmethod
    def delete(self, model_id: int) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def start_training(self, model_id: int) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def list(self, condition: Condition = None) -> ModelListResponse:
        raise NotImplementedError


class BaseIntegrationService(SuperannotateServiceProvider):
    @abstractmethod
    def list(self) -> IntegrationListResponse:
        raise NotImplementedError

    @abstractmethod
    def attach_items(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        integration: entities.IntegrationEntity,
        folder_name: str = None,
    ) -> ServiceResponse:
        raise NotImplementedError


class BaseServiceProvider:
    projects: BaseProjectService
    folders: BaseFolderService
    items: BaseItemService
    annotations: BaseAnnotationService
    custom_fields: BaseCustomFieldService
    annotation_classes: BaseAnnotationClassService
    subsets: BaseSubsetService
    models: BaseModelsService
    integrations: BaseIntegrationService

    @abstractmethod
    def get_team(self, team_id: int) -> TeamResponse:
        raise NotImplementedError

    @abstractmethod
    def get_user(self, team_id: int) -> UserResponse:
        raise NotImplementedError

    @abstractmethod
    def list_templates(self) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def get_limitations(
        self, project: entities.ProjectEntity, folder: entities.FolderEntity
    ) -> UserLimitsResponse:
        raise NotImplementedError

    @abstractmethod
    def get_download_token(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        image_id: int,
        include_original: int = 1,
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def get_upload_token(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        image_id: int,
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def get_s3_upload_auth_token(
        self, project: entities.ProjectEntity, folder: entities.FolderEntity
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def get_annotation_upload_data(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        item_ids: List[int],
    ) -> UploadAnnotationAuthDataResponse:
        raise NotImplementedError

    @abstractmethod
    def prepare_export(
        self,
        project: entities.ProjectEntity,
        folders: List[str],
        annotation_statuses: List[str],
        include_fuse: bool,
        only_pinned: bool,
        integration_id: int,
        export_type: int = None,
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def get_exports(self, project: entities.ProjectEntity) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def get_model_metrics(self, model_id: int) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def get_export(
        self, project: entities.ProjectEntity, export_id: int
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def get_ml_model_download_tokens(
        self, model_id: int
    ) -> DownloadMLModelAuthDataResponse:
        raise NotImplementedError

    @abstractmethod
    def run_prediction(
        self, project: entities.ProjectEntity, ml_model_id: int, image_ids: list
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def get_project_images_count(
        self, project: entities.ProjectEntity
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def search_team_contributors(self, condition: Condition = None) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def invite_contributors(
        self, team_id: int, team_role: int, emails: List[str]
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def validate_saqul_query(
        self, project: entities.ProjectEntity, query: str
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def saqul_query(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity = None,
        query: str = None,
        subset_id: int = None,
    ) -> ServiceResponse:
        raise NotImplementedError
