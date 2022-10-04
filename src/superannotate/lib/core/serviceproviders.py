from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import Dict
from typing import List

from lib.core import entities
from lib.core.conditions import Condition
from lib.core.service_types import FolderListResponse
from lib.core.service_types import FolderResponse
from lib.core.service_types import ItemListResponse
from lib.core.service_types import ProjectListResponse
from lib.core.service_types import ProjectResponse
from lib.core.service_types import ServiceResponse
from lib.core.service_types import SettingsListResponse
from lib.core.service_types import UserLimitsResponse
from lib.core.types import Attachment
from lib.core.types import AttachmentMeta


class BaseClient(ABC):
    def __init__(self, team_id: int, api_url: str, token: str):
        self.team_id = team_id
        self._api_url = api_url
        self._token = token

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
    def share(self, project: entities.ProjectEntity, users: list):
        raise NotImplementedError

    @abstractmethod
    def set_project_workflow_attributes(
        self, project: entities.ProjectEntity, attributes: list
    ):
        raise NotImplementedError


class BaseFolderService(SuperannotateServiceProvider):
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


class BaseAnnotationClassService(SuperannotateServiceProvider):
    @abstractmethod
    def list(self, condition: Condition = None) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def create(
        self, project_id: int, item: entities.AnnotationClassEntity
    ) -> ServiceResponse:
        raise NotImplementedError

    @abstractmethod
    def create_multiple(
        self, project_id: int, items: List[entities.AnnotationClassEntity]
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
    def list_by_names(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        names: List[str],
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


class BaseServiceProvider:
    projects: BaseProjectService
    folders: BaseFolderService
    items: BaseItemService
    annotation_classes: BaseAnnotationClassService

    @abstractmethod
    def get_limitations(
        self, project: entities.ProjectEntity, folder: entities.FolderEntity
    ) -> UserLimitsResponse:
        raise NotImplementedError


#
# @abstractmethod
# def attach_files(
#     self,
#     project_id: int,
#     folder_id: int,
#     team_id: int,
#     files: List[Dict],
#     annotation_status_code: int,
#     upload_state_code: int,
#     meta: Dict,
# ):
#     raise NotImplementedError
#
# @abstractmethod
# def get_annotation_classes(
#     self, project_id: int, team_id: int, name_prefix: str = None
# ):
#     raise NotImplementedError
#
# @abstractmethod
# def share_project_bulk(self, project_id: int, team_id: int, users: Iterable):
#     raise NotImplementedError
#
# @abstractmethod
# def invite_contributors(
#     self, team_id: int, team_role: int, emails: Iterable
# ) -> Tuple[List[str], List[str]]:
#     raise NotImplementedError
#
# @abstractmethod
# def prepare_export(
#     self,
#     project_id: int,
#     team_id: int,
#     folders: List[str],
#     annotation_statuses: Iterable[Any],
#     include_fuse: bool,
#     only_pinned: bool,
# ):
#     raise NotImplementedError
#
# @abstractmethod
# def search_team_contributors(self, team_id: int, query_string: str = None):
#     raise NotImplementedError
#
# @abstractmethod
# def get_project_settings(self, project_id: int, team_id: int):
#     raise NotImplementedError
#
# @abstractmethod
# def set_project_settings(self, project_id: int, team_id: int, data: List):
#     raise NotImplementedError
#
# @abstractmethod
# def get_project_workflows(self, project_id: int, team_id: int):
#     raise NotImplementedError
#
# @abstractmethod
# def list_images(self, query_string):
#     raise NotImplementedError
#
# @abstractmethod
# def get_project(self, uuid: int, team_id: int):
#     raise NotImplementedError
#
# @abstractmethod
# def set_project_workflow(self, project_id: int, team_id: int, data: Dict):
#     raise NotImplementedError
#
# def delete_folders(self, project_id: int, team_id: int, folder_ids: List[int]):
#     raise NotImplementedError
#
# def get_folder(self, query_string: str):
#     raise NotImplementedError
#
# def get_folders(self, query_string: str = None, params: dict = None):
#     raise NotImplementedError
#
# def create_folder(self, project_id: int, team_id: int, folder_name: str):
#     raise NotImplementedError
#
# def update_folder(self, project_id: int, team_id: int, folder_data: dict):
#     raise NotImplementedError
#
# def list_items(self, query_params: str) -> ServiceResponse:
#     raise NotImplementedError
#
# def get_download_token(
#     self,
#     project_id: int,
#     team_id: int,
#     folder_id: int,
#     image_id: int,
#     include_original: int = 1,
# ) -> dict:
#     raise NotImplementedError
#
# def get_upload_token(
#     self,
#     project_id: int,
#     team_id: int,
#     folder_id: int,
#     image_id: int,
# ) -> dict:
#     raise NotImplementedError
#
# def update_image(self, image_id: int, team_id: int, project_id: int, data: dict):
#     raise NotImplementedError
#
# def copy_items_between_folders_transaction(
#     self,
#     team_id: int,
#     project_id: int,
#     from_folder_id: int,
#     to_folder_id: int,
#     items: List[str],
#     include_annotations: bool = False,
#     include_pin: bool = False,
# ) -> int:
#     raise NotImplementedError
#
# def move_images_between_folders(
#     self,
#     team_id: int,
#     project_id: int,
#     from_folder_id: int,
#     to_folder_id: int,
#     images: List[str],
# ) -> List[str]:
#     """
#     Returns list of moved images.
#     """
#     raise NotImplementedError
#
# def get_progress(
#     self, project_id: int, team_id: int, poll_id: int
# ) -> Tuple[int, int]:
#     raise NotImplementedError
#
# def await_progress(
#     self, project_id: int, team_id: int, poll_id: int, items_count
# ) -> Tuple[int, int]:
#     raise NotImplementedError
#
# def set_images_statuses_bulk(
#     self,
#     image_names: List[str],
#     team_id: int,
#     project_id: int,
#     folder_id: int,
#     annotation_status: int,
# ):
#     raise NotImplementedError
#
# def delete_items(self, project_id: int, team_id: int, item_ids: List[int]):
#     raise NotImplementedError
#
# def assign_items(
#     self,
#     team_id: int,
#     project_id: int,
#     folder_name: str,
#     user: str,
#     item_names: list,
# ) -> ServiceResponse:
#     raise NotImplementedError
#
# def get_bulk_images(
#     self, project_id: int, team_id: int, folder_id: int, images: List[str]
# ) -> List[dict]:
#     raise NotImplementedError
#
# def un_assign_folder(
#     self,
#     team_id: int,
#     project_id: int,
#     folder_name: str,
# ):
#     raise NotImplementedError
#
# def assign_folder(
#     self, team_id: int, project_id: int, folder_name: str, users: list
# ):
#     raise NotImplementedError
#
# def un_assign_items(
#     self,
#     team_id: int,
#     project_id: int,
#     folder_name: str,
#     item_names: list,
# ):
#     raise NotImplementedError
#
# def un_share_project(
#     self,
#     team_id: int,
#     project_id: int,
#     user_id: str,
# ):
#     raise NotImplementedError
#
# def get_exports(self, team_id: int, project_id: int):
#     raise NotImplementedError
#
# def get_export(self, team_id: int, project_id: int, export_id: int):
#     raise NotImplementedError
#
# def get_project_images_count(self, team_id: int, project_id: int):
#     raise NotImplementedError
#
# def get_s3_upload_auth_token(self, team_id: int, folder_id: int, project_id: int):
#     raise NotImplementedError
#
# def delete_annotation_class(
#     self, team_id: int, project_id: int, annotation_class_id: int
# ):
#     raise NotImplementedError
#
# def set_annotation_classes(self, team_id: int, project_id: int, data: list):
#     raise NotImplementedError
#
# def set_project_workflow_bulk(self, project_id: int, team_id: int, steps: list):
#     raise NotImplementedError
#
# def set_project_workflow_attributes_bulk(
#     self, project_id: int, team_id: int, attributes: list
# ):
#     raise NotImplementedError
#
# def get_annotation_upload_data(
#     self, project_id: int, team_id: int, image_ids: List[int], folder_id: int
# ) -> ServiceResponse:
#     raise NotImplementedError
#
# def get_templates(self, team_id: int):
#     raise NotImplementedError
#
# def start_model_training(self, team_id: int, hyper_parameters: dict) -> dict:
#     raise NotImplementedError
#
# def get_model_metrics(self, team_id: int, model_id: int) -> dict:
#     raise NotImplementedError
#
# def bulk_get_folders(self, team_id: int, project_ids: List[int]):
#     raise NotImplementedError
#
# def update_model(self, team_id: int, model_id: int, data: dict):
#     raise NotImplementedError
#
# def delete_model(self, team_id: int, model_id: int):
#     raise NotImplementedError
#
# def get_ml_model_download_tokens(
#     self, team_id: int, model_id: int
# ) -> ServiceResponse:
#     raise NotImplementedError
#
# def run_prediction(
#     self, team_id: int, project_id: int, ml_model_id: int, image_ids: list
# ):
#     raise NotImplementedError
#
# def delete_image_annotations(
#     self,
#     team_id: int,
#     project_id: int,
#     folder_id: int = None,
#     image_names: List[str] = None,
# ) -> dict:
#     raise NotImplementedError
#
# def get_annotations_delete_progress(
#     self, team_id: int, project_id: int, poll_id: int
# ):
#     raise NotImplementedError
#
# def get_limitations(
#     self, team_id: int, project_id: int, folder_id: int = None
# ) -> ServiceResponse:
#     raise NotImplementedError
#
# @abstractmethod
# def get_annotations(
#     self,
#     project_id: int,
#     team_id: int,
#     folder_id: int,
#     items: List[str],
#     reporter: Reporter,
#     callback: Callable = None,
# ) -> List[dict]:
#     raise NotImplementedError
#
# @abstractmethod
# def create_annotation_classes(self, project_id: int, team_id: int, data: List):
#     raise NotImplementedError
#
# @abstractmethod
# async def download_annotations(
#     self,
#     project_id: int,
#     team_id: int,
#     folder_id: int,
#     reporter: Reporter,
#     download_path: str,
#     postfix: str,
#     items: List[str] = None,
#     callback: Callable = None,
# ) -> int:
#     """
#     Returns the number of items downloaded
#     """
#     raise NotImplementedError
#
# def upload_priority_scores(
#     self, team_id: int, project_id: int, folder_id: int, priorities: list
# ) -> dict:
#     raise NotImplementedError
#
# def get_integrations(self, team_id: int) -> List[dict]:
#     raise NotImplementedError
#
# def attach_integrations(
#     self,
#     team_id: int,
#     project_id: int,
#     integration_id: int,
#     folder_id: int,
#     folder_name: str,
# ) -> bool:
#     raise NotImplementedError
#
# def saqul_query(
#     self,
#     team_id: int,
#     project_id: int,
#     folder_id: int,
#     query: str = None,
#     subset_id: int = None,
# ) -> ServiceResponse:
#     raise NotImplementedError
#
# def validate_saqul_query(self, team_id: int, project_id: int, query: str) -> dict:
#     raise NotImplementedError
#
# async def upload_annotations(
#     self,
#     team_id: int,
#     project_id: int,
#     folder_id: int,
#     items_name_file_map: Dict[str, io.StringIO],
# ) -> ServiceResponse:
#     raise NotImplementedError
#
# async def upload_big_annotation(
#     self,
#     team_id: int,
#     project_id: int,
#     folder_id: int,
#     item_id: int,
#     data: io.StringIO,
#     chunk_size: int,
# ) -> bool:
#     raise NotImplementedError
#
# def get_schema(
#     self, team_id: int, project_type: int, version: str
# ) -> ServiceResponse:
#     raise NotImplementedError
#
# def list_sub_sets(self, team_id: int, project_id: int) -> ServiceResponse:
#     raise NotImplementedError
#
# def create_custom_schema(
#     self, team_id: int, project_id: int, schema: dict
# ) -> ServiceResponse:
#     raise NotImplementedError
#
# def get_custom_schema(self, team_id: int, project_id: int) -> ServiceResponse:
#     raise NotImplementedError
#
# def delete_custom_schema(
#     self, team_id: int, project_id: int, fields: List[str]
# ) -> ServiceResponse:
#     raise NotImplementedError
#
# def upload_custom_fields(
#     self, team_id: int, project_id: int, folder_id: int, items: List[dict]
# ) -> ServiceResponse:
#     raise NotImplementedError
#
# def delete_custom_fields(
#     self,
#     team_id: int,
#     project_id: int,
#     folder_id: int,
#     items: List[Dict[str, List[str]]],
# ) -> ServiceResponse:
#     raise NotImplementedError
#
# @abstractmethod
# def list_annotation_classes(
#     self, project_id: int, team_id: int, query_string: str = None
# ):
#     raise NotImplementedError
#
# @abstractmethod
# async def download_big_annotation(
#     self,
#     project_id: int,
#     team_id: int,
#     download_path: str,
#     postfix: str,
#     item: dict,
#     callback: Callable = None,
# ):
#     raise NotImplementedError
#
# @abstractmethod
# async def download_small_annotations(
#     self,
#     project_id: int,
#     team_id: int,
#     folder_id: int,
#     reporter: Reporter,
#     download_path: str,
#     postfix: str,
#     items: List[str] = None,
#     callback: Callable = None,
# ):
#     raise NotImplementedError
#
# @abstractmethod
# def sort_items_by_size(
#     self, item_names: List[str], team_id: int, project_id: int, folder_id: int
# ):
#     raise NotImplementedError
