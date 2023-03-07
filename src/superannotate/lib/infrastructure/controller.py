import io
import logging
import os
from abc import ABCMeta
from pathlib import Path
from typing import Callable
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

import lib.core as constances
from lib.core import usecases
from lib.core.conditions import Condition
from lib.core.conditions import CONDITION_EQ as EQ
from lib.core.entities import AttachmentEntity
from lib.core.entities import BaseItemEntity
from lib.core.entities import ConfigEntity
from lib.core.entities import ContributorEntity
from lib.core.entities import FolderEntity
from lib.core.entities import ImageEntity
from lib.core.entities import MLModelEntity
from lib.core.entities import ProjectEntity
from lib.core.entities import SettingEntity
from lib.core.entities import TeamEntity
from lib.core.entities.classes import AnnotationClassEntity
from lib.core.entities.integrations import IntegrationEntity
from lib.core.exceptions import AppException
from lib.core.reporter import Reporter
from lib.core.response import Response
from lib.infrastructure.helpers import timed_lru_cache
from lib.infrastructure.repositories import S3Repository
from lib.infrastructure.serviceprovider import ServiceProvider
from lib.infrastructure.services.http_client import HttpClient
from lib.infrastructure.utils import extract_project_folder


def build_condition(**kwargs) -> Condition:
    condition = Condition.get_empty_condition()
    if any(kwargs.values()):
        for key, value in ((key, value) for key, value in kwargs.items() if value):
            condition = condition & Condition(key, value, EQ)
    return condition


class BaseManager:
    def __init__(self, service_provider: ServiceProvider):
        self.service_provider = service_provider


class ProjectManager(BaseManager):
    def get_by_id(self, project_id):
        use_case = usecases.GetProjectByIDUseCase(
            project_id=project_id, service_provider=self.service_provider
        )
        response = use_case.execute()
        return response

    def get_by_name(self, name: str):
        use_case = usecases.GetProjectByNameUseCase(
            name=name, service_provider=self.service_provider
        )
        response = use_case.execute()
        if response.errors:
            raise AppException(response.errors)
        return response

    def get_metadata(
        self,
        project: ProjectEntity,
        include_annotation_classes: bool = False,
        include_settings: bool = False,
        include_workflow: bool = False,
        include_contributors: bool = False,
        include_complete_image_count: bool = False,
    ):
        use_case = usecases.GetProjectMetaDataUseCase(
            project=project,
            service_provider=self.service_provider,
            include_annotation_classes=include_annotation_classes,
            include_settings=include_settings,
            include_workflow=include_workflow,
            include_contributors=include_contributors,
            include_complete_image_count=include_complete_image_count,
        )
        return use_case.execute()

    def create(self, entity: ProjectEntity) -> Response:
        use_case = usecases.CreateProjectUseCase(
            project=entity, service_provider=self.service_provider
        )
        return use_case.execute()

    def list(self, condition: Condition):
        use_case = usecases.GetProjectsUseCase(
            condition=condition,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def delete(self, name: str):
        use_case = usecases.DeleteProjectUseCase(
            project_name=name, service_provider=self.service_provider
        )
        return use_case.execute()

    def update(self, entity: ProjectEntity) -> Response:
        use_case = usecases.UpdateProjectUseCase(
            entity, service_provider=self.service_provider
        )
        return use_case.execute()

    def set_settings(self, project: ProjectEntity, settings: List[SettingEntity]):
        use_case = usecases.UpdateSettingsUseCase(
            to_update=settings,
            service_provider=self.service_provider,
            project=project,
        )
        return use_case.execute()

    def list_settings(self, project: ProjectEntity):
        use_case = usecases.GetSettingsUseCase(
            service_provider=self.service_provider, project=project
        )
        return use_case.execute()

    def list_workflow(self, project: ProjectEntity):
        use_case = usecases.GetWorkflowsUseCase(
            project=project, service_provider=self.service_provider
        )
        return use_case.execute()

    def set_workflows(self, project: ProjectEntity, steps: List):
        use_case = usecases.SetWorkflowUseCase(
            service_provider=self.service_provider,
            steps=steps,
            project=project,
        )
        return use_case.execute()

    def add_contributors(
        self,
        team: TeamEntity,
        project: ProjectEntity,
        contributors: List[ContributorEntity],
    ):
        project = self.get_metadata(project).data
        use_case = usecases.AddContributorsToProject(
            team=team,
            project=project,
            contributors=contributors,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def un_share(self, project: ProjectEntity, user_id: str):
        use_case = usecases.UnShareProjectUseCase(
            service_provider=self.service_provider,
            project=project,
            user_id=user_id,
        )
        return use_case.execute()

    def assign_items(
        self, project: ProjectEntity, folder: FolderEntity, item_names: list, user: str
    ):
        use_case = usecases.AssignItemsUseCase(
            project=project,
            service_provider=self.service_provider,
            folder=folder,
            item_names=item_names,
            user=user,
        )
        return use_case.execute()

    def un_assign_items(
        self, project: ProjectEntity, folder: FolderEntity, item_names: list
    ):
        use_case = usecases.UnAssignItemsUseCase(
            project=project,
            service_provider=self.service_provider,
            folder=folder,
            item_names=item_names,
        )
        return use_case.execute()

    def upload_priority_scores(
        self, project: ProjectEntity, folder: FolderEntity, scores, project_folder_name
    ):
        use_case = usecases.UploadPriorityScoresUseCase(
            reporter=Reporter(),
            project=project,
            folder=folder,
            scores=scores,
            service_provider=self.service_provider,
            project_folder_name=project_folder_name,
        )
        return use_case.execute()


class AnnotationClassManager(BaseManager):
    @timed_lru_cache(seconds=3600)
    def __get_auth_data(self, project: ProjectEntity, folder: FolderEntity):
        response = self.service_provider.get_s3_upload_auth_token(project, folder)
        if not response.ok:
            raise AppException(response.error)
        return response.data

    def _get_s3_repository(self, project: ProjectEntity, folder: FolderEntity):
        auth_data = self.__get_auth_data(project, folder)
        return S3Repository(
            auth_data["accessKeyId"],
            auth_data["secretAccessKey"],
            auth_data["sessionToken"],
            auth_data["bucket"],
        )

    def create(self, project: ProjectEntity, annotation_class: AnnotationClassEntity):
        use_case = usecases.CreateAnnotationClassUseCase(
            annotation_class=annotation_class,
            project=project,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def create_multiple(
        self, project: ProjectEntity, annotation_classes: List[AnnotationClassEntity]
    ):
        use_case = usecases.CreateAnnotationClassesUseCase(
            service_provider=self.service_provider,
            annotation_classes=annotation_classes,
            project=project,
        )
        return use_case.execute()

    def list(self, condition: Condition):
        use_case = usecases.GetAnnotationClassesUseCase(
            service_provider=self.service_provider,
            condition=condition,
        )
        return use_case.execute()

    def delete(self, project: ProjectEntity, annotation_class: AnnotationClassEntity):
        use_case = usecases.DeleteAnnotationClassUseCase(
            annotation_class=annotation_class,
            project=project,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def copy_multiple(
        self,
        source_project: ProjectEntity,
        source_folder: FolderEntity,
        source_item: BaseItemEntity,
        destination_project: ProjectEntity,
        destination_folder: FolderEntity,
        destination_item: BaseItemEntity,
    ):
        use_case = usecases.CopyImageAnnotationClasses(
            from_project=source_project,
            from_folder=source_folder,
            from_image=source_item,
            to_project=destination_project,
            to_folder=destination_folder,
            to_image=destination_item,
            service_provider=self.service_provider,
            from_project_s3_repo=self._get_s3_repository(source_project, source_folder),
            to_project_s3_repo=self._get_s3_repository(
                destination_project, destination_folder
            ),
        )
        return use_case.execute()

    def download(self, project: ProjectEntity, download_path: str):
        use_case = usecases.DownloadAnnotationClassesUseCase(
            project=project,
            download_path=download_path,
            service_provider=self.service_provider,
        )
        return use_case.execute()


class FolderManager(BaseManager):
    def create(self, project: ProjectEntity, folder: FolderEntity):
        use_case = usecases.CreateFolderUseCase(
            project=project,
            folder=folder,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def get_by_id(self, folder_id, project_id, team_id):
        use_case = usecases.GetFolderByIDUseCase(
            folder_id=folder_id,
            project_id=project_id,
            team_id=team_id,
            service_provider=self.service_provider,
        )
        result = use_case.execute()
        return result

    def list(self, project: ProjectEntity, condition: Condition = None):
        use_case = usecases.SearchFoldersUseCase(
            project=project, service_provider=self.service_provider, condition=condition
        )
        return use_case.execute()

    def delete_multiple(self, project: ProjectEntity, folders: List[FolderEntity]):
        use_case = usecases.DeleteFolderUseCase(
            project=project,
            folders=folders,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def get_by_name(self, project: ProjectEntity, name: str = None):
        name = Controller.get_folder_name(name)
        use_case = usecases.GetFolderUseCase(
            project=project,
            folder_name=name,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def assign_users(
        self, project: ProjectEntity, folder: FolderEntity, users: List[str]
    ):
        use_case = usecases.AssignFolderUseCase(
            service_provider=self.service_provider,
            project=project,
            folder=folder,
            users=users,
        )
        return use_case.execute()


class ItemManager(BaseManager):
    def get_by_name(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        name: str,
        include_custom_metadata: bool = False,
    ):
        use_case = usecases.GetItem(
            reporter=Reporter(),
            project=project,
            folder=folder,
            item_name=name,
            service_provider=self.service_provider,
            include_custom_metadata=include_custom_metadata,
        )
        return use_case.execute()

    def get_by_id(self, item_id: int, project: ProjectEntity):
        use_case = usecases.GetItemByIDUseCase(
            item_id=item_id,
            project=project,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def list(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        condition: Condition = None,
        recursive: bool = False,
        include_custom_metadata: bool = False,
    ):
        use_case = usecases.ListItems(
            project=project,
            folder=folder,
            service_provider=self.service_provider,
            recursive=recursive,
            search_condition=condition,
            include_custom_metadata=include_custom_metadata,
        )
        return use_case.execute()

    def attach(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        attachments: List[AttachmentEntity],
        annotation_status: str,
    ):
        use_case = usecases.AttachItems(
            reporter=Reporter(),
            project=project,
            folder=folder,
            attachments=attachments,
            annotation_status=annotation_status,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def delete(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        item_names: List[str] = None,
    ):
        use_case = usecases.DeleteItemsUseCase(
            project=project,
            folder=folder,
            item_names=item_names,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def copy_multiple(
        self,
        project: ProjectEntity,
        from_folder: FolderEntity,
        to_folder: FolderEntity,
        item_names: List[str] = None,
        include_annotations: bool = False,
    ):
        use_case = usecases.CopyItems(
            reporter=Reporter(),
            project=project,
            from_folder=from_folder,
            to_folder=to_folder,
            item_names=item_names,
            service_provider=self.service_provider,
            include_annotations=include_annotations,
        )
        return use_case.execute()

    def move_multiple(
        self,
        project: ProjectEntity,
        from_folder: FolderEntity,
        to_folder: FolderEntity,
        item_names: List[str] = None,
    ):
        use_case = usecases.MoveItems(
            reporter=Reporter(),
            project=project,
            from_folder=from_folder,
            to_folder=to_folder,
            item_names=item_names,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def set_annotation_statuses(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        annotation_status: str,
        item_names: List[str] = None,
    ):
        use_case = usecases.SetAnnotationStatues(
            Reporter(),
            project=project,
            folder=folder,
            annotation_status=annotation_status,
            item_names=item_names,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def set_approval_statuses(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        approval_status: str,
        item_names: List[str] = None,
    ):
        use_case = usecases.SetApprovalStatues(
            Reporter(),
            project=project,
            folder=folder,
            approval_status=approval_status,
            item_names=item_names,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def update(self, project: ProjectEntity, item: BaseItemEntity):
        use_case = usecases.UpdateItemUseCase(
            project=project, service_provider=self.service_provider, item=item
        )
        return use_case.execute()


class AnnotationManager(BaseManager):
    def __init__(self, service_provider: ServiceProvider, config: ConfigEntity):
        super().__init__(service_provider)
        self._config = config

    def list(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        item_names: List[str],
        verbose=True,
    ):
        use_case = usecases.GetAnnotations(
            config=self._config,
            reporter=Reporter(log_info=verbose, log_warning=verbose),
            project=project,
            folder=folder,
            item_names=item_names,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def download(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        destination: str,
        recursive: bool,
        item_names: Optional[List[str]],
        callback: Optional[Callable],
    ):
        use_case = usecases.DownloadAnnotations(
            config=self._config,
            reporter=Reporter(),
            project=project,
            folder=folder,
            destination=destination,
            recursive=recursive,
            item_names=item_names,
            service_provider=self.service_provider,
            callback=callback,
        )
        return use_case.execute()

    def download_image_annotations(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        image_name: str,
        destination: str,
    ):
        use_case = usecases.DownloadImageAnnotationsUseCase(
            project=project,
            folder=folder,
            image_name=image_name,
            service_provider=self.service_provider,
            destination=destination,
        )
        return use_case.execute()

    def delete(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        item_names: Optional[List[str]] = None,
    ):
        use_case = usecases.DeleteAnnotations(
            project=project,
            folder=folder,
            service_provider=self.service_provider,
            image_names=item_names,
        )
        return use_case.execute()

    def upload_multiple(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        annotations: List[dict],
        keep_status: bool,
    ):
        use_case = usecases.UploadAnnotationsUseCase(
            reporter=Reporter(),
            project=project,
            folder=folder,
            annotations=annotations,
            service_provider=self.service_provider,
            keep_status=keep_status,
        )
        return use_case.execute()

    def upload_from_folder(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        annotation_paths: List[str],
        team: TeamEntity,
        keep_status: bool = False,
        client_s3_bucket=None,
        is_pre_annotations: bool = False,
        folder_path: str = None,
    ):
        use_case = usecases.UploadAnnotationsFromFolderUseCase(
            project=project,
            folder=folder,
            team=team,
            annotation_paths=annotation_paths,
            service_provider=self.service_provider,
            pre_annotation=is_pre_annotations,
            client_s3_bucket=client_s3_bucket,
            reporter=Reporter(),
            folder_path=folder_path,
            keep_status=keep_status,
        )
        return use_case.execute()

    def upload_image_annotations(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        image: ImageEntity,
        team: TeamEntity,
        annotations: dict,
        mask: io.BytesIO = None,
        verbose: bool = True,
        keep_status: bool = False,
    ):
        use_case = usecases.UploadAnnotationUseCase(
            project=project,
            folder=folder,
            team=team,
            service_provider=self.service_provider,
            image=image,
            annotations=annotations,
            mask=mask,
            verbose=verbose,
            reporter=Reporter(),
            keep_status=keep_status,
        )
        return use_case.execute()


class CustomFieldManager(BaseManager):
    def create_schema(self, project: ProjectEntity, schema: dict):
        use_case = usecases.CreateCustomSchemaUseCase(
            reporter=Reporter(),
            project=project,
            schema=schema,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def get_schema(self, project: ProjectEntity):
        use_case = usecases.GetCustomSchemaUseCase(
            reporter=Reporter(),
            project=project,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def delete_schema(self, project: ProjectEntity, fields: List[str]):
        use_case = usecases.DeleteCustomSchemaUseCase(
            reporter=Reporter(),
            project=project,
            fields=fields,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def upload_values(
        self, project: ProjectEntity, folder: FolderEntity, items: List[dict]
    ):
        use_case = usecases.UploadCustomValuesUseCase(
            reporter=Reporter(),
            project=project,
            folder=folder,
            items=items,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def delete_values(
        self, project: ProjectEntity, folder: FolderEntity, items: List[dict]
    ):
        use_case = usecases.DeleteCustomValuesUseCase(
            reporter=Reporter(),
            project=project,
            folder=folder,
            items=items,
            service_provider=self.service_provider,
        )
        return use_case.execute()


class ModelManager(BaseManager):
    def list(self, condition: Condition):
        use_case = usecases.SearchMLModels(
            condition=condition, service_provider=self.service_provider
        )
        return use_case.execute()

    def run_prediction(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        items_list: list,
        model_name: str,
    ):
        use_case = usecases.RunPredictionUseCase(
            project=project,
            ml_model_name=model_name,
            images_list=items_list,
            service_provider=self.service_provider,
            folder=folder,
        )
        return use_case.execute()

    def download(self, model_data: dict, download_path: str):
        model = MLModelEntity(
            id=model_data["id"],
            name=model_data["name"],
            path=model_data["path"],
            config_path=model_data["config_path"],
            team_id=model_data["team_id"],
            training_status=model_data["training_status"],
            is_global=model_data["is_global"],
        )
        use_case = usecases.DownloadMLModelUseCase(
            model=model,
            download_path=download_path,
            service_provider=self.service_provider,
        )
        return use_case.execute()


class IntegrationManager(BaseManager):
    def list(self):
        use_case = usecases.GetIntegrations(
            reporter=Reporter(), service_provider=self.service_provider
        )
        return use_case.execute()

    def attach_items(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        integration: IntegrationEntity,
        folder_path: str,
    ):
        use_case = usecases.AttachIntegrations(
            reporter=Reporter(),
            service_provider=self.service_provider,
            project=project,
            folder=folder,
            integration=integration,
            folder_path=folder_path,
        )
        return use_case.execute()


class SubsetManager(BaseManager):
    def list(self, project: ProjectEntity):
        use_case = usecases.ListSubsetsUseCase(
            project=project,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def add_items(self, project: ProjectEntity, subset: str, items: List[dict]):
        root_folder = FolderEntity(id=project.id, name="root")
        use_case = usecases.AddItemsToSubsetUseCase(
            reporter=Reporter(),
            project=project,
            subset_name=subset,
            items=items,
            service_provider=self.service_provider,
            root_folder=root_folder,
        )

        return use_case.execute()


class BaseController(metaclass=ABCMeta):
    SESSIONS = {}

    def __init__(self, config: ConfigEntity):
        self._config = config
        self._logger = logging.getLogger("sa")
        self._testing = os.getenv("SA_TESTING", "False").lower() in ("true", "1", "t")
        self._token = config.API_TOKEN
        self._team_data = None
        self._s3_upload_auth_data = None
        self._projects = None
        self._folders = None
        self._teams = None
        self._images = None
        self._items = None
        self._integrations = None
        self._ml_models = None
        self._user_id = None
        self._reporter = None

        http_client = HttpClient(
            api_url=config.API_URL, token=config.API_TOKEN, verify_ssl=config.VERIFY_SSL
        )

        self.service_provider = ServiceProvider(http_client)
        self._team = self.get_team().data
        self.annotation_classes = AnnotationClassManager(self.service_provider)
        self.projects = ProjectManager(self.service_provider)
        self.folders = FolderManager(self.service_provider)
        self.items = ItemManager(self.service_provider)
        self.annotations = AnnotationManager(self.service_provider, config)
        self.custom_fields = CustomFieldManager(self.service_provider)
        self.subsets = SubsetManager(self.service_provider)
        self.models = ModelManager(self.service_provider)
        self.integrations = IntegrationManager(self.service_provider)

    @staticmethod
    def validate_token(token: str):
        try:
            int(token.split("=")[-1])
        except ValueError:
            raise AppException("Invalid token.")
        return token

    @property
    def user_id(self):
        if not self._user_id:
            self._user_id, _ = self.get_team()
        return self._user_id

    @property
    def team(self):
        return self._team

    def get_team(self):
        return usecases.GetTeamUseCase(
            service_provider=self.service_provider, team_id=self.team_id
        ).execute()

    @property
    def team_data(self):
        if not self._team_data:
            self._team_data = self.team
        return self._team_data

    @property
    def team_id(self) -> int:
        if not self._token:
            raise AppException("Invalid credentials provided.")
        return int(self._token.split("=")[-1])

    @staticmethod
    def get_default_reporter(
        log_info: bool = True,
        log_warning: bool = True,
        disable_progress_bar: bool = False,
        log_debug: bool = True,
    ) -> Reporter:
        return Reporter(log_info, log_warning, disable_progress_bar, log_debug)

    @property
    def s3_repo(self):
        return S3Repository


class Controller(BaseController):
    DEFAULT = None

    @classmethod
    def set_default(cls, obj):
        cls.DEFAULT = obj
        return cls.DEFAULT

    def get_folder_by_id(self, folder_id: int, project_id: int) -> FolderEntity:
        response = self.folders.get_by_id(
            folder_id=folder_id, project_id=project_id, team_id=self.team_id
        )

        if response.errors:
            raise AppException(response.errors)

        return response.data

    def get_project_by_id(self, project_id: int) -> ProjectEntity:
        response = self.projects.get_by_id(project_id=project_id)
        if response.errors:
            raise AppException(response.errors)

        return response.data

    def get_item_by_id(self, item_id: int, project_id: int):
        project = self.get_project_by_id(project_id=project_id)
        response = self.items.get_by_id(item_id=item_id, project=project)

        if response.errors:
            raise AppException(response.errors)

        return response.data

    def get_project_folder_by_path(
        self, path: Union[str, Path]
    ) -> Tuple[ProjectEntity, FolderEntity]:
        project_name, folder_name = extract_project_folder(path)
        return self.get_project_folder(project_name, folder_name)

    def get_project_folder(
        self, project_name: str, folder_name: str = None
    ) -> Tuple[ProjectEntity, FolderEntity]:
        project = self.get_project(project_name)
        folder = self.get_folder(project, folder_name)
        return project, folder

    def get_project(self, name: str) -> ProjectEntity:
        project = self.projects.get_by_name(name).data
        if not project:
            raise AppException("Project not found.")
        return project

    def get_folder(self, project: ProjectEntity, name: str = None) -> FolderEntity:
        folder = self.folders.get_by_name(project, name).data
        if not folder:
            raise AppException("Folder not found.")
        return folder

    @staticmethod
    def get_folder_name(name: str = None):
        if name:
            return name
        return "root"

    def upload_image_to_project(
        self,
        project_name: str,
        folder_name: str,
        image_name: str,
        image: Union[str, io.BytesIO] = None,
        annotation_status: str = None,
        image_quality_in_editor: str = None,
        from_s3_bucket=None,
    ):
        project = self.get_project(project_name)
        folder = self.get_folder(project, folder_name)
        image_bytes = None
        image_path = None
        if isinstance(image, (str, Path)):
            image_path = image
        else:
            image_bytes = image

        return usecases.UploadImageToProject(
            project=project,
            folder=folder,
            s3_repo=self.s3_repo,
            service_provider=self.service_provider,
            image_path=image_path,
            image_bytes=image_bytes,
            image_name=image_name,
            from_s3_bucket=from_s3_bucket,
            annotation_status=annotation_status,
            image_quality_in_editor=image_quality_in_editor,
        ).execute()

    def upload_images_to_project(
        self,
        project_name: str,
        folder_name: str,
        paths: List[str],
        annotation_status: str = None,
        image_quality_in_editor: str = None,
        from_s3_bucket=None,
    ):
        project = self.get_project(project_name)
        folder = self.get_folder(project, folder_name)

        return usecases.UploadImagesToProject(
            project=project,
            folder=folder,
            s3_repo=self.s3_repo,
            service_provider=self.service_provider,
            paths=paths,
            from_s3_bucket=from_s3_bucket,
            annotation_status=annotation_status,
            image_quality_in_editor=image_quality_in_editor,
        )

    def upload_images_from_folder_to_project(
        self,
        project_name: str,
        folder_name: str,
        folder_path: str,
        extensions: Optional[List[str]] = None,
        annotation_status: str = None,
        exclude_file_patterns: Optional[List[str]] = None,
        recursive_sub_folders: Optional[bool] = None,
        image_quality_in_editor: str = None,
        from_s3_bucket=None,
    ):
        project = self.get_project(project_name)
        folder = self.get_folder(project, folder_name)

        return usecases.UploadImagesFromFolderToProject(
            project=project,
            folder=folder,
            s3_repo=self.s3_repo,
            service_provider=self.service_provider,
            folder_path=folder_path,
            extensions=extensions,
            annotation_status=annotation_status,
            from_s3_bucket=from_s3_bucket,
            exclude_file_patterns=exclude_file_patterns,
            recursive_sub_folders=recursive_sub_folders,
            image_quality_in_editor=image_quality_in_editor,
        )

    def prepare_export(
        self,
        project_name: str,
        folder_names: List[str],
        include_fuse: bool,
        only_pinned: bool,
        annotation_statuses: List[str] = None,
    ):
        project = self.get_project(project_name)
        use_case = usecases.PrepareExportUseCase(
            project=project,
            folder_names=folder_names,
            service_provider=self.service_provider,
            include_fuse=include_fuse,
            only_pinned=only_pinned,
            annotation_statuses=annotation_statuses,
        )
        return use_case.execute()

    def search_team_contributors(self, **kwargs):
        condition = build_condition(**kwargs)
        use_case = usecases.SearchContributorsUseCase(
            service_provider=self.service_provider,
            team_id=self.team_id,
            condition=condition,
        )
        return use_case.execute()

    def _get_image(
        self,
        project: ProjectEntity,
        image_name: str,
        folder: FolderEntity = None,
    ) -> ImageEntity:
        response = usecases.GetImageUseCase(
            service_provider=self.service_provider,
            project=project,
            folder=folder,
            image_name=image_name,
        ).execute()
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def update(self, project: ProjectEntity, folder: FolderEntity):
        use_case = usecases.UpdateFolderUseCase(
            service_provider=self.service_provider, folder=folder, project=project
        )
        return use_case.execute()

    def un_assign_folder(self, project_name: str, folder_name: str):
        project_entity = self.get_project(project_name)
        folder = self.get_folder(project_entity, folder_name)
        use_case = usecases.UnAssignFolderUseCase(
            service_provider=self.service_provider,
            project=project_entity,
            folder=folder,
        )
        return use_case.execute()

    def get_exports(self, project_name: str, return_metadata: bool):
        project = self.get_project(project_name)

        use_case = usecases.GetExportsUseCase(
            service_provider=self.service_provider,
            project=project,
            return_metadata=return_metadata,
        )
        return use_case.execute()

    def get_project_image_count(
        self, project_name: str, folder_name: str, with_all_subfolders: bool
    ):

        project = self.get_project(project_name)
        folder = self.get_folder(project=project, name=folder_name)

        use_case = usecases.GetProjectImageCountUseCase(
            service_provider=self.service_provider,
            project=project,
            folder=folder,
            with_all_sub_folders=with_all_subfolders,
        )

        return use_case.execute()

    def download_image(
        self,
        project_name: str,
        image_name: str,
        download_path: str,
        folder_name: str = None,
        image_variant: str = None,
        include_annotations: bool = None,
        include_fuse: bool = None,
        include_overlay: bool = None,
    ):
        project = self.get_project(project_name)
        folder = self.get_folder(project, folder_name)
        image = self._get_image(project, image_name, folder)

        use_case = usecases.DownloadImageUseCase(
            reporter=self.get_default_reporter(),
            project=project,
            folder=folder,
            image=image,
            service_provider=self.service_provider,
            download_path=download_path,
            image_variant=image_variant,
            include_annotations=include_annotations,
            include_fuse=include_fuse,
            include_overlay=include_overlay,
        )
        return use_case.execute()

    def download_export(
        self,
        project_name: str,
        export_name: str,
        folder_path: str,
        extract_zip_contents: bool,
        to_s3_bucket: bool,
    ):
        project = self.get_project(project_name)
        use_case = usecases.DownloadExportUseCase(
            service_provider=self.service_provider,
            project=project,
            export_name=export_name,
            folder_path=folder_path,
            extract_zip_contents=extract_zip_contents,
            to_s3_bucket=to_s3_bucket,
            reporter=self.get_default_reporter(),
        )
        return use_case.execute()

    def consensus(
        self,
        project_name: str,
        folder_names: list,
        # export_path: str,
        image_list: list,
        annot_type: str,
        # show_plots: bool,
    ):
        project = self.get_project(project_name)

        use_case = usecases.ConsensusUseCase(
            project=project,
            folder_names=folder_names,
            image_list=image_list,
            annotation_type=annot_type,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def validate_annotations(self, project_type: str, annotation: dict):
        use_case = usecases.ValidateAnnotationUseCase(
            reporter=self.get_default_reporter(),
            project_type=constances.ProjectType.get_value(project_type),
            annotation=annotation,
            team_id=self.team_id,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def invite_contributors_to_team(self, emails: list, set_admin: bool):
        use_case = usecases.InviteContributorsToTeam(
            team=self.team,
            emails=emails,
            set_admin=set_admin,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def upload_videos(
        self,
        project_name: str,
        folder_name: str,
        paths: List[str],
        start_time: float,
        extensions: List[str] = None,
        exclude_file_patterns: List[str] = None,
        end_time: Optional[float] = None,
        target_fps: Optional[int] = None,
        annotation_status: Optional[str] = None,
        image_quality_in_editor: Optional[str] = None,
    ):
        project = self.get_project(project_name)
        folder = self.get_folder(project, folder_name)

        use_case = usecases.UploadVideosAsImages(
            reporter=self.get_default_reporter(),
            service_provider=self.service_provider,
            project=project,
            folder=folder,
            s3_repo=self.s3_repo,
            paths=paths,
            target_fps=target_fps,
            extensions=extensions,
            exclude_file_patterns=exclude_file_patterns,
            start_time=start_time,
            end_time=end_time,
            annotation_status=annotation_status,
            image_quality_in_editor=image_quality_in_editor,
        )
        return use_case.execute()

    def get_annotations_per_frame(
        self, project_name: str, folder_name: str, video_name: str, fps: int
    ):
        project = self.get_project(project_name)
        folder = self.get_folder(project, folder_name)

        use_case = usecases.GetVideoAnnotationsPerFrame(
            config=self._config,
            reporter=self.get_default_reporter(),
            project=project,
            folder=folder,
            video_name=video_name,
            fps=fps,
            service_provider=self.service_provider,
        )
        return use_case.execute()

    def query_entities(
        self, project_name: str, folder_name: str, query: str = None, subset: str = None
    ):
        project = self.get_project(project_name)
        folder = self.get_folder(project, folder_name)

        use_case = usecases.QueryEntitiesUseCase(
            reporter=self.get_default_reporter(),
            project=project,
            folder=folder,
            query=query,
            subset=subset,
            service_provider=self.service_provider,
        )
        return use_case.execute()
