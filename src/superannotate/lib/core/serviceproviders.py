import io
from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional

from lib.core import entities
from lib.core.conditions import Condition
from lib.core.enums import CustomFieldEntityEnum
from lib.core.jsx_conditions import Query
from lib.core.reporter import Reporter
from lib.core.service_types import AnnotationClassListResponse
from lib.core.service_types import FolderListResponse
from lib.core.service_types import FolderResponse
from lib.core.service_types import IntegrationListResponse
from lib.core.service_types import ListCategoryResponse
from lib.core.service_types import ProjectListResponse
from lib.core.service_types import ProjectResponse
from lib.core.service_types import ServiceResponse
from lib.core.service_types import SettingsListResponse
from lib.core.service_types import TeamResponse
from lib.core.service_types import UploadAnnotationAuthDataResponse
from lib.core.service_types import UploadAnnotationsResponse
from lib.core.service_types import UserLimitsResponse
from lib.core.service_types import UserResponse
from lib.core.service_types import WMCustomFieldResponse
from lib.core.service_types import WMProjectListResponse
from lib.core.service_types import WMScoreListResponse
from lib.core.service_types import WMUserListResponse
from lib.core.service_types import WorkflowListResponse
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
    def token(self):
        return self._token

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
        headers: Dict = None,
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def jsx_paginate(
        self,
        url: str,
        method: str = Literal["get", "post"],
        body_query: Query = None,
        query_params: Dict = None,
        headers: Dict = None,
        chunk_size: int = 100,
        item_type: Any = None,
    ) -> ServiceResponse:
        raise NotImplementedError


class SuperannotateServiceProvider(ABC):
    def __init__(self, client: BaseClient):
        self.client = client


class BaseWorkManagementService(SuperannotateServiceProvider):
    @abstractmethod
    def get_workflow(self, pk: int) -> entities.WorkflowEntity:
        raise NotImplementedError

    @abstractmethod
    def list_workflows(self, query: Query) -> WorkflowListResponse:
        raise NotImplementedError

    @abstractmethod
    def list_workflow_statuses(self, project_id: int, workflow_id: int):
        raise NotImplementedError

    @abstractmethod
    def list_workflow_roles(self, project_id: int, workflow_id: int):
        raise NotImplementedError

    @abstractmethod
    def list_custom_field_templates(
        self,
        entity: CustomFieldEntityEnum,
        parent_entity: CustomFieldEntityEnum,
        context: dict = None,
    ):
        raise NotImplementedError

    @abstractmethod
    def create_project_custom_field_template(self, data: dict):
        raise NotImplementedError

    @abstractmethod
    def list_project_custom_entities(self, project_id: int):
        raise NotImplementedError

    @abstractmethod
    def list_projects(
        self, body_query: Query, chunk_size: int = 100
    ) -> WMProjectListResponse:
        raise NotImplementedError

    @abstractmethod
    def search_projects(
        self, body_query: Query, chunk_size: int = 100
    ) -> WMProjectListResponse:
        raise NotImplementedError

    @abstractmethod
    def list_project_categories(self, project_id: int) -> ListCategoryResponse:
        raise NotImplementedError

    @abstractmethod
    def create_project_categories(
        self, project_id: int, categories: List[str]
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def list_users(
        self,
        body_query: Query,
        parent_entity: str = "Team",
        chunk_size=100,
        project_id: int = None,
        include_custom_fields=False,
    ) -> WMUserListResponse:
        raise NotImplementedError

    @abstractmethod
    def create_custom_field_template(
        self,
        name: str,
        component_id: int,
        entity: CustomFieldEntityEnum,
        parent_entity: CustomFieldEntityEnum,
        component_payload: Optional[dict] = None,
        access: Optional[dict] = None,
        entity_context: Optional[dict] = None,
    ) -> WMCustomFieldResponse:
        raise NotImplementedError

    @abstractmethod
    def delete_custom_field_template(
        self,
        pk: int,
        entity: CustomFieldEntityEnum,
        parent_entity: CustomFieldEntityEnum,
        entity_context: Optional[dict] = None,
    ):
        raise NotImplementedError

    @abstractmethod
    def set_custom_field_value(
        self,
        entity_id: int,
        template_id: int,
        data: dict,
        entity: CustomFieldEntityEnum,
        parent_entity: CustomFieldEntityEnum,
        context: Optional[dict] = None,
    ):
        raise NotImplementedError

    @abstractmethod
    def update_user_activity(
        self, body_query: Query, action=Literal["resume", "pause"]
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def list_scores(self) -> WMScoreListResponse:
        raise NotImplementedError

    @abstractmethod
    def create_score(
        self,
        name: str,
        description: Optional[str],
        score_type: Literal["rating", "number", "radio"],
        payload: dict,
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def delete_score(self, score_id: int) -> ServiceResponse:
        raise NotImplementedError


class BaseProjectService(SuperannotateServiceProvider):
    @abstractmethod
    def get_by_id(self, project_id: int):
        raise NotImplementedError

    @abstractmethod
    def create(self, entity: entities.ProjectEntity) -> ProjectResponse:
        raise NotImplementedError

    @abstractmethod
    def attach_editor_template(
        self, team: entities.TeamEntity, project: entities.ProjectEntity, template: dict
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def get_editor_template(
        self, organization_id: str, project_id: int
    ) -> ServiceResponse:
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
    def list_steps(self, project: entities.ProjectEntity):
        raise NotImplementedError

    @abstractmethod
    def list_keypoint_steps(self, project: entities.ProjectEntity):
        raise NotImplementedError

    @abstractmethod
    def set_step(self, project: entities.ProjectEntity, step: entities.StepEntity):
        raise NotImplementedError

    @abstractmethod
    def set_keypoint_steps(self, project: entities.ProjectEntity, steps, connections):
        raise NotImplementedError

    @abstractmethod
    def set_steps(self, project: entities.ProjectEntity, steps: list):
        raise NotImplementedError

    @abstractmethod
    def share(self, project: entities.ProjectEntity, users: list) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def un_share(self, project: entities.ProjectEntity, user_id) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def set_project_step_attributes(
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
    def update(self, project: entities.ProjectEntity, item: entities.BaseItemEntity):
        raise NotImplementedError

    @abstractmethod
    def attach(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        attachments: List[Attachment],
        upload_state_code,
        annotation_status_code=None,
        meta: Dict[str, AttachmentMeta] = None,
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
    def copy_move_multiple(
        self,
        project: entities.ProjectEntity,
        from_folder: entities.FolderEntity,
        to_folder: entities.FolderEntity,
        item_names: List[str],
        duplicate_strategy: Literal["skip", "replace", "replace_annotations_only"],
        operation: Literal["copy", "move"],
        include_annotations: bool = True,
        include_pin: bool = False,
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def await_copy(self, project: entities.ProjectEntity, poll_id: int, items_count):
        raise NotImplementedError

    @abstractmethod
    def await_copy_move(
        self, project: entities.ProjectEntity, poll_id: int, items_count
    ):
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

    @abstractmethod
    def bulk_attach_categories(
        self, project_id: int, folder_id: int, item_category_map: Dict[int, int]
    ) -> bool:
        raise NotImplementedError


class BaseAnnotationService(SuperannotateServiceProvider):
    @abstractmethod
    async def get_big_annotation(
        self,
        project: entities.ProjectEntity,
        item: entities.BaseItemEntity,
        reporter: Reporter,
        transform_version: str = None,
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
        transform_version: str = None,
    ) -> List[dict]:
        raise NotImplementedError

    @abstractmethod
    def get_upload_chunks(
        self,
        project: entities.ProjectEntity,
        item_ids: List[int],
        chunk_size: int = 1000,
    ) -> Dict[str, List]:
        raise NotImplementedError

    @abstractmethod
    async def download_big_annotation(
        self,
        project: entities.ProjectEntity,
        download_path: str,
        item: entities.BaseItemEntity,
        callback: Callable = None,
        transform_version: str = None,
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
        transform_version: str = None,
    ):
        raise NotImplementedError

    @abstractmethod
    async def upload_small_annotations(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        items_name_data_map: Dict[str, dict],
        transform_version: str = None,
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
        transform_version: str = None,
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

    @abstractmethod
    def get_item_annotations(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        item_id: int,
        transform_version: str = "llmJsonV2",
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def set_item_annotations(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        item_id: int,
        data: dict,
        overwrite: bool,
        transform_version: str = "llmJsonV2",
        etag: str = None,
    ) -> ServiceResponse:
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
        options: Dict[str, str] = None,
    ) -> ServiceResponse:
        raise NotImplementedError


class BaseExploreService(SuperannotateServiceProvider):
    MAX_ITEMS_COUNT: int
    CHUNK_SIZE: int
    SAQUL_CHUNK_SIZE: int

    @abstractmethod
    def list_fields(self, project: entities.ProjectEntity, item_ids: List[int]):
        raise NotImplementedError

    @abstractmethod
    def create_schema(self, project: entities.ProjectEntity, schema: dict):
        raise NotImplementedError

    @abstractmethod
    def get_schema(self, project: entities.ProjectEntity):
        raise NotImplementedError

    @abstractmethod
    def delete_fields(self, project: entities.ProjectEntity, fields: List[str]):
        raise NotImplementedError

    @abstractmethod
    def upload_fields(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        items: List[dict],
    ):
        raise NotImplementedError

    @abstractmethod
    def delete_values(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        items: List[Dict[str, List[str]]],
    ):
        raise NotImplementedError

    @abstractmethod
    def list_subsets(
        self, project: entities.ProjectEntity, condition: Condition = None
    ):
        raise NotImplementedError

    @abstractmethod
    def create_multiple_subsets(self, project: entities.ProjectEntity, name: List[str]):
        raise NotImplementedError

    @abstractmethod
    def add_items_to_subset(
        self,
        project: entities.ProjectEntity,
        subset: entities.SubSetEntity,
        item_ids: List[int],
    ):
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

    @abstractmethod
    def query_item_count(
        self,
        project: entities.ProjectEntity,
        query: str = None,
    ) -> ServiceResponse:
        raise NotImplementedError


class BaseTelemetryScoringService(SuperannotateServiceProvider):
    @abstractmethod
    def get_score_values(self, project_id: int, item_id: int, user_id: str):
        raise NotImplementedError

    @abstractmethod
    def set_score_values(
        self,
        project_id: int,
        data: List[dict],
    ) -> ServiceResponse:
        raise NotImplementedError


class BaseServiceProvider:
    projects: BaseProjectService
    folders: BaseFolderService
    items: BaseItemService
    annotations: BaseAnnotationService
    annotation_classes: BaseAnnotationClassService
    integrations: BaseIntegrationService
    explore: BaseExploreService
    work_management: BaseWorkManagementService
    item_service: Any

    @abstractmethod
    def get_role_id(self, project: entities.ProjectEntity, role_name: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def get_category_id(
        self, project: entities.ProjectEntity, category_name: str
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    def get_role_name(self, project: entities.ProjectEntity, role_id: int) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_annotation_status_value(
        self, project: entities.ProjectEntity, status_name: str
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    def get_annotation_status_name(
        self, project: entities.ProjectEntity, status_value: int
    ) -> str:
        raise NotImplementedError

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
        include_fuse: bool,
        only_pinned: bool,
        integration_id: int,
        annotation_statuses: List[str] = None,
        export_type: int = None,
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def get_exports(self, project: entities.ProjectEntity) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def get_export(
        self, project: entities.ProjectEntity, export_id: int
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
    def list_custom_field_names(
        self,
        context: dict,
        entity: CustomFieldEntityEnum,
        parent: CustomFieldEntityEnum,
    ) -> List[str]:
        raise NotImplementedError

    @abstractmethod
    def get_custom_field_id(
        self,
        context: dict,
        field_name: str,
        entity: CustomFieldEntityEnum,
        parent: CustomFieldEntityEnum,
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    def get_custom_field_name(
        self,
        context: dict,
        field_id: int,
        entity: CustomFieldEntityEnum,
        parent: CustomFieldEntityEnum,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_custom_field_component_id(
        self,
        context: dict,
        field_id: int,
        entity: CustomFieldEntityEnum,
        parent: CustomFieldEntityEnum,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_custom_fields_templates(
        self,
        context: dict,
        entity: CustomFieldEntityEnum,
        parent: CustomFieldEntityEnum,
    ):
        raise NotImplementedError
