import copy
import io
import os
from abc import ABCMeta
from pathlib import Path
from typing import Callable
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

import lib.core as constances
from lib.core import usecases
from lib.core.conditions import Condition
from lib.core.conditions import CONDITION_EQ as EQ
from lib.core.entities import AnnotationClassEntity
from lib.core.entities import AttachmentEntity
from lib.core.entities import FolderEntity
from lib.core.entities import ImageEntity
from lib.core.entities import MLModelEntity
from lib.core.entities import ProjectEntity
from lib.core.entities import SettingEntity
from lib.core.entities.integrations import IntegrationEntity
from lib.core.exceptions import AppException
from lib.core.reporter import Reporter
from lib.core.response import Response
from lib.infrastructure.helpers import timed_lru_cache
from lib.infrastructure.repositories import AnnotationClassRepository
from lib.infrastructure.repositories import FolderRepository
from lib.infrastructure.repositories import ImageRepository
from lib.infrastructure.repositories import IntegrationRepository
from lib.infrastructure.repositories import ItemRepository
from lib.infrastructure.repositories import MLModelRepository
from lib.infrastructure.repositories import ProjectRepository
from lib.infrastructure.repositories import ProjectSettingsRepository
from lib.infrastructure.repositories import S3Repository
from lib.infrastructure.repositories import TeamRepository
from lib.infrastructure.repositories import WorkflowRepository
from lib.infrastructure.services import SuperannotateBackendService
from superannotate.logger import get_default_logger
from superannotate_schemas.validators import AnnotationValidators


def build_condition(**kwargs) -> Condition:
    condition = Condition.get_empty_condition()
    if any(kwargs.values()):
        for key, value in ((key, value) for key, value in kwargs.items() if value):
            condition = condition & Condition(key, value, EQ)
    return condition


class BaseController(metaclass=ABCMeta):
    SESSIONS = {}

    def __init__(self, token: str, host: str, ssl_verify: bool, version: str):
        self._version = version
        self._logger = get_default_logger()
        self._testing = os.getenv("SA_TESTING", "False").lower() in ("true", "1", "t")
        self._token = token
        self._backend_client = SuperannotateBackendService(
            api_url=host,
            auth_token=token,
            logger=self._logger,
            verify_ssl=ssl_verify,
            testing=self._testing,
        )
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
        self._team = self._get_team()

    @staticmethod
    def validate_token(token: str):
        try:
            int(token.split("=")[-1])
        except ValueError:
            raise AppException("Invalid token.")
        return token

    @property
    def backend_client(self):
        return self._backend_client

    @property
    def user_id(self):
        if not self._user_id:
            self._user_id, _ = self.get_team()
        return self._user_id

    @property
    def projects(self):
        if not self._projects:
            self._projects = ProjectRepository(self._backend_client)
        return self._projects

    @property
    def folders(self):
        if not self._folders:
            self._folders = FolderRepository(self._backend_client)
        return self._folders

    @property
    def team(self):
        return self._team

    def _get_team(self):
        response = usecases.GetTeamUseCase(
            teams=self.teams, team_id=self.team_id
        ).execute()
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def get_team(self):
        return usecases.GetTeamUseCase(teams=self.teams, team_id=self.team_id).execute()

    @property
    def ml_models(self):
        if not self._ml_models:
            self._ml_models = MLModelRepository(self._backend_client, self.team_id)
        return self._ml_models

    @property
    def teams(self):
        return TeamRepository(self.backend_client)

    @property
    def team_data(self):
        if not self._team_data:
            self._team_data = self.team
        return self._team_data

    @property
    def images(self):
        if not self._images:
            self._images = ImageRepository(self._backend_client)
        return self._images

    @property
    def items(self):
        if not self._items:
            self._items = ItemRepository(self._backend_client)
        return self._items

    def get_integrations_repo(self, team_id: int):
        if not self._integrations:
            self._integrations = IntegrationRepository(self._backend_client, team_id)
        return self._integrations

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

    @timed_lru_cache(seconds=3600)
    def get_auth_data(self, project_id: int, team_id: int, folder_id: int):
        response = self._backend_client.get_s3_upload_auth_token(
            team_id, folder_id, project_id
        )
        if "error" in response:
            raise AppException(response.get("error"))
        return response

    def get_s3_repository(self, team_id: int, project_id: int, folder_id: int):
        auth_data = self.get_auth_data(project_id, team_id, folder_id)
        return S3Repository(
            auth_data["accessKeyId"],
            auth_data["secretAccessKey"],
            auth_data["sessionToken"],
            auth_data["bucket"],
        )

    @property
    def s3_repo(self):
        return S3Repository

    @property
    def annotation_validators(self) -> AnnotationValidators:
        return AnnotationValidators()


class Controller(BaseController):
    DEFAULT = None

    @classmethod
    def set_default(cls, obj):
        cls.DEFAULT = obj
        return cls.DEFAULT

    def _get_project(self, name: str) -> ProjectEntity:
        use_case = usecases.GetProjectByNameUseCase(
            name=name,
            team_id=self.team_id,
            projects=ProjectRepository(service=self._backend_client),
        )
        response = use_case.execute()
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def _get_folder(self, project: ProjectEntity, name: str = None):
        name = self.get_folder_name(name)
        use_case = usecases.GetFolderUseCase(
            project=project,
            folders=self.folders,
            folder_name=name,
            team_id=self.team_id,
        )
        response = use_case.execute()
        if not response.data or response.errors:
            raise AppException("Folder not found.")
        return response.data

    @staticmethod
    def get_folder_name(name: str = None):
        if name:
            return name
        return "root"

    def search_project(
        self,
        name: str = None,
        include_complete_image_count=False,
        statuses: Union[List[str], Tuple[str]] = (),
        **kwargs,
    ) -> Response:
        condition = Condition.get_empty_condition()
        if name:
            condition &= Condition("name", name, EQ)
        if include_complete_image_count:
            condition &= Condition(
                "completeImagesCount", include_complete_image_count, EQ
            )
        for status in statuses:
            condition &= Condition(
                "status", constances.ProjectStatus.get_value(status), EQ
            )

        condition &= build_condition(**kwargs)
        use_case = usecases.GetProjectsUseCase(
            condition=condition,
            projects=self.projects,
            team_id=self.team_id,
        )
        return use_case.execute()

    def create_project(
        self,
        name: str,
        description: str,
        project_type: str,
        settings: Iterable[SettingEntity] = None,
        classes: Iterable = tuple(),
        workflows: Iterable = tuple(),
        **extra_kwargs,
    ) -> Response:

        try:
            project_type = constances.ProjectType[project_type.upper()].value
        except KeyError:
            raise AppException(
                "Please provide a valid project type: Vector, Pixel, Document, or Video."
            )
        entity = ProjectEntity(
            name=name,
            description=description,
            type=project_type,
            team_id=self.team_id,
            settings=settings if settings else [],
            **extra_kwargs,
        )
        use_case = usecases.CreateProjectUseCase(
            project=entity,
            projects=self.projects,
            backend_service_provider=self._backend_client,
            workflows_repo=WorkflowRepository,
            annotation_classes_repo=AnnotationClassRepository,
            workflows=workflows,
            classes=[
                AnnotationClassEntity(**annotation_class)
                for annotation_class in classes
            ],
        )
        return use_case.execute()

    def delete_project(self, name: str):
        use_case = usecases.DeleteProjectUseCase(
            project_name=name,
            team_id=self.team_id,
            projects=self.projects,
        )
        return use_case.execute()

    def update_project(self, name: str, project_data: dict) -> Response:
        project = self._get_project(name)
        use_case = usecases.UpdateProjectUseCase(project, project_data, self.projects)
        return use_case.execute()

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
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)
        image_bytes = None
        image_path = None
        if isinstance(image, (str, Path)):
            image_path = image
        else:
            image_bytes = image

        return usecases.UploadImageToProject(
            project=project,
            folder=folder,
            settings=ProjectSettingsRepository(
                service=self._backend_client, project=project
            ),
            s3_repo=self.s3_repo,
            backend_client=self._backend_client,
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
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)

        return usecases.UploadImagesToProject(
            project=project,
            folder=folder,
            settings=ProjectSettingsRepository(
                service=self._backend_client, project=project
            ),
            s3_repo=self.s3_repo,
            backend_client=self._backend_client,
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
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)

        return usecases.UploadImagesFromFolderToProject(
            project=project,
            folder=folder,
            settings=ProjectSettingsRepository(
                service=self._backend_client, project=project
            ),
            s3_repo=self.s3_repo,
            backend_client=self._backend_client,
            folder_path=folder_path,
            extensions=extensions,
            annotation_status=annotation_status,
            from_s3_bucket=from_s3_bucket,
            exclude_file_patterns=exclude_file_patterns,
            recursive_sub_folders=recursive_sub_folders,
            image_quality_in_editor=image_quality_in_editor,
        )

    def clone_project(
        self,
        name: str,
        from_name: str,
        project_description: str,
        copy_annotation_classes=True,
        copy_settings=True,
        copy_workflow=True,
        copy_contributors=False,
    ):

        project = self._get_project(from_name)
        project_to_create = copy.copy(project)
        reporter = self.get_default_reporter()
        reporter.track(
            "external", project.upload_state == constances.UploadState.EXTERNAL.value
        )
        project_to_create.name = name
        if project_description is not None:
            project_to_create.description = project_description
        use_case = usecases.CloneProjectUseCase(
            reporter=reporter,
            project=project,
            project_to_create=project_to_create,
            projects=self.projects,
            settings_repo=ProjectSettingsRepository,
            workflows_repo=WorkflowRepository,
            annotation_classes_repo=AnnotationClassRepository,
            backend_service_provider=self._backend_client,
            include_contributors=copy_contributors,
            include_settings=copy_settings,
            include_workflow=copy_workflow,
            include_annotation_classes=copy_annotation_classes,
        )
        return use_case.execute()

    def interactive_attach_urls(
        self,
        project_name: str,
        files: List[ImageEntity],
        folder_name: str = None,
        annotation_status: str = None,
        upload_state_code: int = None,
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)

        return usecases.InteractiveAttachFileUrlsUseCase(
            project=project,
            folder=folder,
            attachments=files,
            backend_service_provider=self._backend_client,
            annotation_status=annotation_status,
            upload_state_code=upload_state_code,
        )

    def create_folder(self, project: str, folder_name: str):
        project = self._get_project(project)
        folder = FolderEntity(
            name=folder_name, project_id=project.id, team_id=project.team_id
        )
        use_case = usecases.CreateFolderUseCase(
            project=project,
            folder=folder,
            folders=self.folders,
        )
        return use_case.execute()

    def get_folder(self, project_name: str, folder_name: str):
        project = self._get_project(project_name)
        use_case = usecases.GetFolderUseCase(
            project=project,
            folders=self.folders,
            folder_name=folder_name,
            team_id=self.team_id,
        )
        return use_case.execute()

    def search_folders(
        self, project_name: str, folder_name: str = None, include_users=False, **kwargs
    ):
        condition = build_condition(**kwargs)
        project = self._get_project(project_name)
        use_case = usecases.SearchFoldersUseCase(
            project=project,
            folders=self.folders,
            condition=condition,
            folder_name=folder_name,
            include_users=include_users,
        )
        return use_case.execute()

    def delete_folders(self, project_name: str, folder_names: List[str]):
        project = self._get_project(project_name)
        folders = self.search_folders(project_name=project_name).data

        use_case = usecases.DeleteFolderUseCase(
            project=project,
            folders=self.folders,
            folders_to_delete=[
                folder for folder in folders if folder.name in folder_names
            ],
        )
        return use_case.execute()

    def prepare_export(
        self,
        project_name: str,
        folder_names: List[str],
        include_fuse: bool,
        only_pinned: bool,
        annotation_statuses: List[str] = None,
    ):

        project = self._get_project(project_name)
        use_case = usecases.PrepareExportUseCase(
            project=project,
            folder_names=folder_names,
            folders=self.folders,
            backend_service_provider=self._backend_client,
            include_fuse=include_fuse,
            only_pinned=only_pinned,
            annotation_statuses=annotation_statuses,
        )
        return use_case.execute()

    def search_team_contributors(self, **kwargs):
        condition = build_condition(**kwargs)
        use_case = usecases.SearchContributorsUseCase(
            backend_service_provider=self._backend_client,
            team_id=self.team_id,
            condition=condition,
        )
        return use_case.execute()

    def search_images(
        self,
        project_name: str,
        folder_path: str = None,
        annotation_status: str = None,
        image_name_prefix: str = None,
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_path)

        use_case = usecases.GetImagesUseCase(
            project=project,
            folder=folder,
            images=self.images,
            annotation_status=annotation_status,
            image_name_prefix=image_name_prefix,
        )
        return use_case.execute()

    def _get_image(
        self,
        project: ProjectEntity,
        image_name: str,
        folder: FolderEntity = None,
    ) -> ImageEntity:
        response = usecases.GetImageUseCase(
            service=self._backend_client,
            project=project,
            folder=folder,
            image_name=image_name,
            images=self.images,
        ).execute()
        if response.errors:
            raise AppException(response.errors)
        return response.data

    def get_image(
        self, project_name: str, image_name: str, folder_path: str = None
    ) -> ImageEntity:
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_path)
        return self._get_image(project, image_name, folder)

    def update_folder(self, project_name: str, folder_name: str, folder_data: dict):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)
        for field, value in folder_data.items():
            setattr(folder, field, value)
        use_case = usecases.UpdateFolderUseCase(
            folders=self.folders,
            folder=folder,
        )
        return use_case.execute()

    def copy_image(
        self,
        from_project_name: str,
        from_folder_name: str,
        to_project_name: str,
        to_folder_name: str,
        image_name: str,
        copy_annotation_status: bool = False,
        move: bool = False,
    ):
        from_project = self._get_project(from_project_name)
        to_project = self._get_project(to_project_name)
        to_folder = self._get_folder(to_project, to_folder_name)
        use_case = usecases.CopyImageUseCase(
            from_project=from_project,
            from_folder=self._get_folder(from_project, from_folder_name),
            to_project=to_project,
            to_folder=to_folder,
            backend_service=self._backend_client,
            image_name=image_name,
            images=self.images,
            project_settings=ProjectSettingsRepository(
                self._backend_client, to_project
            ).get_all(),
            s3_repo=self.s3_repo,
            copy_annotation_status=copy_annotation_status,
            move=move,
        )
        return use_case.execute()

    def copy_image_annotation_classes(
        self,
        from_project_name: str,
        from_folder_name: str,
        to_project_name: str,
        to_folder_name: str,
        image_name: str,
    ):
        from_project = self._get_project(from_project_name)
        from_folder = self._get_folder(from_project, from_folder_name)
        image = self._get_image(from_project, folder=from_folder, image_name=image_name)
        to_project = self._get_project(to_project_name)
        to_folder = self._get_folder(to_project, to_folder_name)
        uploaded_image = self._get_image(
            to_project, folder=to_folder, image_name=image_name
        )

        use_case = usecases.CopyImageAnnotationClasses(
            from_project=from_project,
            to_project=to_project,
            from_image=image,
            to_image=uploaded_image,
            from_project_annotation_classes=AnnotationClassRepository(
                self._backend_client, from_project
            ),
            to_project_annotation_classes=AnnotationClassRepository(
                self._backend_client, to_project
            ),
            from_project_s3_repo=self.get_s3_repository(
                image.team_id, image.project_id, image.folder_id
            ),
            to_project_s3_repo=self.get_s3_repository(
                uploaded_image.team_id,
                uploaded_image.project_id,
                uploaded_image.folder_id,
            ),
            backend_service_provider=self._backend_client,
        )
        return use_case.execute()

    def update_image(
        self, project_name: str, image_name: str, folder_name: str = None, **kwargs
    ):
        image = self.get_image(
            project_name=project_name, image_name=image_name, folder_path=folder_name
        )
        for item, val in kwargs.items():
            setattr(image, item, val)
        use_case = usecases.UpdateImageUseCase(image=image, images=self.images)
        return use_case.execute()

    def bulk_copy_images(
        self,
        project_name: str,
        from_folder_name: str,
        to_folder_name: str,
        image_names: List[str],
        include_annotations: bool,
        include_pin: bool,
    ):
        project = self._get_project(project_name)
        from_folder = self._get_folder(project, from_folder_name)
        to_folder = self._get_folder(project, to_folder_name)
        use_case = usecases.ImagesBulkCopyUseCase(
            project=project,
            from_folder=from_folder,
            to_folder=to_folder,
            image_names=image_names,
            backend_service_provider=self._backend_client,
            include_annotations=include_annotations,
            include_pin=include_pin,
        )
        return use_case.execute()

    def bulk_move_images(
        self,
        project_name: str,
        from_folder_name: str,
        to_folder_name: str,
        image_names: List[str],
    ):
        project = self._get_project(project_name)
        from_folder = self._get_folder(project, from_folder_name)
        to_folder = self._get_folder(project, to_folder_name)
        use_case = usecases.ImagesBulkMoveUseCase(
            project=project,
            from_folder=from_folder,
            to_folder=to_folder,
            image_names=image_names,
            backend_service_provider=self._backend_client,
        )
        return use_case.execute()

    def get_project_metadata(
        self,
        project_name: str,
        include_annotation_classes: bool = False,
        include_settings: bool = False,
        include_workflow: bool = False,
        include_contributors: bool = False,
        include_complete_image_count: bool = False,
    ):
        project = self._get_project(project_name)

        use_case = usecases.GetProjectMetaDataUseCase(
            project=project,
            service=self._backend_client,
            annotation_classes=AnnotationClassRepository(
                service=self._backend_client, project=project
            ),
            settings=ProjectSettingsRepository(
                service=self._backend_client, project=project
            ),
            workflows=WorkflowRepository(service=self._backend_client, project=project),
            projects=ProjectRepository(service=self._backend_client),
            include_annotation_classes=include_annotation_classes,
            include_settings=include_settings,
            include_workflow=include_workflow,
            include_contributors=include_contributors,
            include_complete_image_count=include_complete_image_count,
        )
        return use_case.execute()

    def get_project_settings(self, project_name: str):
        project_entity = self._get_project(project_name)
        use_case = usecases.GetSettingsUseCase(
            settings=ProjectSettingsRepository(
                service=self._backend_client, project=project_entity
            ),
        )
        return use_case.execute()

    def get_project_workflow(self, project_name: str):
        project_entity = self._get_project(project_name)
        use_case = usecases.GetWorkflowsUseCase(
            project=project_entity,
            workflows=WorkflowRepository(
                service=self._backend_client, project=project_entity
            ),
            annotation_classes=AnnotationClassRepository(
                service=self._backend_client, project=project_entity
            ),
        )
        return use_case.execute()

    def search_annotation_classes(self, project_name: str, name_contains: str = None):
        project_entity = self._get_project(project_name)
        condition = None
        if name_contains:
            condition = Condition("name", name_contains, EQ) & Condition(
                "pattern", True, EQ
            )
        use_case = usecases.GetAnnotationClassesUseCase(
            classes=AnnotationClassRepository(
                service=self._backend_client, project=project_entity
            ),
            condition=condition,
        )
        return use_case.execute()

    def set_project_settings(self, project_name: str, new_settings: List[dict]):
        project_entity = self._get_project(project_name)
        use_case = usecases.UpdateSettingsUseCase(
            projects=self.projects,
            settings=ProjectSettingsRepository(
                service=self._backend_client, project=project_entity
            ),
            to_update=new_settings,
            backend_service_provider=self._backend_client,
            project_id=project_entity.id,
            team_id=project_entity.team_id,
        )
        return use_case.execute()

    def delete_items(
        self,
        project_name: str,
        folder_name: str,
        items: List[str] = None,
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)

        use_case = usecases.DeleteItemsUseCase(
            project=project,
            folder=folder,
            items=self.items,
            item_names=items,
            backend_service_provider=self._backend_client,
        )
        return use_case.execute()

    def assign_items(
        self, project_name: str, folder_name: str, item_names: list, user: str
    ):
        project_entity = self.get_project_metadata(
            project_name, include_contributors=True
        ).data["project"]
        folder = self._get_folder(project_entity, folder_name)
        use_case = usecases.AssignItemsUseCase(
            project=project_entity,
            service=self._backend_client,
            folder=folder,
            item_names=item_names,
            user=user,
        )
        return use_case.execute()

    def un_assign_items(self, project_name, folder_name, item_names):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)
        use_case = usecases.UnAssignItemsUseCase(
            project_entity=project,
            service=self._backend_client,
            folder=folder,
            item_names=item_names,
        )
        return use_case.execute()

    def un_assign_folder(self, project_name: str, folder_name: str):
        project_entity = self._get_project(project_name)
        folder = self._get_folder(project_entity, folder_name)
        use_case = usecases.UnAssignFolderUseCase(
            service=self._backend_client,
            project_entity=project_entity,
            folder=folder,
        )
        return use_case.execute()

    def assign_folder(self, project_name: str, folder_name: str, users: List[str]):
        project_entity = self._get_project(project_name)
        folder = self._get_folder(project_entity, folder_name)
        use_case = usecases.AssignFolderUseCase(
            service=self._backend_client,
            project_entity=project_entity,
            folder=folder,
            users=users,
        )
        return use_case.execute()

    def un_share_project(self, project_name: str, user_id: str):
        project_entity = self._get_project(project_name)
        use_case = usecases.UnShareProjectUseCase(
            service=self._backend_client,
            project_entity=project_entity,
            user_id=user_id,
        )
        return use_case.execute()

    def download_image_annotations(
        self, project_name: str, folder_name: str, image_name: str, destination: str
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project=project, name=folder_name)
        use_case = usecases.DownloadImageAnnotationsUseCase(
            service=self._backend_client,
            project=project,
            folder=folder,
            image_name=image_name,
            images=ImageRepository(service=self._backend_client),
            destination=destination,
            annotation_classes=AnnotationClassRepository(
                service=self._backend_client, project=project
            ),
        )
        return use_case.execute()

    def get_exports(self, project_name: str, return_metadata: bool):
        project = self._get_project(project_name)

        use_case = usecases.GetExportsUseCase(
            service=self._backend_client,
            project=project,
            return_metadata=return_metadata,
        )
        return use_case.execute()

    def get_project_image_count(
        self, project_name: str, folder_name: str, with_all_subfolders: bool
    ):

        project = self._get_project(project_name)
        folder = self._get_folder(project=project, name=folder_name)

        use_case = usecases.GetProjectImageCountUseCase(
            service=self._backend_client,
            project=project,
            folder=folder,
            with_all_sub_folders=with_all_subfolders,
        )

        return use_case.execute()

    def create_annotation_class(
        self,
        project_name: str,
        name: str,
        color: str,
        attribute_groups: List[dict],
        class_type: str,
    ):
        project = self._get_project(project_name)
        annotation_classes = AnnotationClassRepository(
            project=project, service=self._backend_client
        )
        annotation_class = AnnotationClassEntity(
            name=name, color=color, attribute_groups=attribute_groups, type=class_type
        )
        use_case = usecases.CreateAnnotationClassUseCase(
            annotation_classes=annotation_classes,
            annotation_class=annotation_class,
            project=project,
        )
        return use_case.execute()

    def delete_annotation_class(self, project_name: str, annotation_class_name: str):
        project = self._get_project(project_name)
        use_case = usecases.DeleteAnnotationClassUseCase(
            annotation_class_name=annotation_class_name,
            annotation_classes_repo=AnnotationClassRepository(
                service=self._backend_client,
                project=project,
            ),
            project_name=project_name,
        )
        return use_case.execute()

    def get_annotation_class(self, project_name: str, annotation_class_name: str):
        project = self._get_project(project_name)
        use_case = usecases.GetAnnotationClassUseCase(
            annotation_class_name=annotation_class_name,
            annotation_classes_repo=AnnotationClassRepository(
                service=self._backend_client,
                project=project,
            ),
        )
        return use_case.execute()

    def download_annotation_classes(self, project_name: str, download_path: str):
        project = self._get_project(project_name)
        use_case = usecases.DownloadAnnotationClassesUseCase(
            annotation_classes_repo=AnnotationClassRepository(
                service=self._backend_client,
                project=project,
            ),
            download_path=download_path,
            project_name=project_name,
        )
        return use_case.execute()

    def create_annotation_classes(self, project_name: str, annotation_classes: list):
        project = self._get_project(project_name)

        use_case = usecases.CreateAnnotationClassesUseCase(
            service=self._backend_client,
            annotation_classes_repo=AnnotationClassRepository(
                service=self._backend_client,
                project=project,
            ),
            annotation_classes=annotation_classes,
            project=project,
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
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)
        image = self._get_image(project, image_name, folder)

        use_case = usecases.DownloadImageUseCase(
            project=project,
            folder=folder,
            image=image,
            images=self.images,
            classes=AnnotationClassRepository(self._backend_client, project),
            backend_service_provider=self._backend_client,
            download_path=download_path,
            image_variant=image_variant,
            include_annotations=include_annotations,
            include_fuse=include_fuse,
            include_overlay=include_overlay,
            annotation_classes=AnnotationClassRepository(
                service=self._backend_client, project=project
            ),
        )
        return use_case.execute()

    def set_project_workflow(self, project_name: str, steps: list):
        project = self._get_project(project_name)
        use_case = usecases.SetWorkflowUseCase(
            service=self._backend_client,
            annotation_classes_repo=AnnotationClassRepository(
                service=self._backend_client, project=project
            ),
            workflow_repo=WorkflowRepository(
                service=self._backend_client, project=project
            ),
            steps=steps,
            project=project,
        )
        return use_case.execute()

    def upload_annotations_from_folder(
        self,
        project_name: str,
        folder_name: str,
        annotation_paths: List[str],
        client_s3_bucket=None,
        is_pre_annotations: bool = False,
        folder_path: str = None,
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)
        use_case = usecases.UploadAnnotationsUseCase(
            project=project,
            folder=folder,
            images=self.images,
            team=self.team_data,
            annotation_paths=annotation_paths,
            backend_service_provider=self._backend_client,
            annotation_classes=AnnotationClassRepository(
                service=self._backend_client, project=project
            ).get_all(),
            pre_annotation=is_pre_annotations,
            client_s3_bucket=client_s3_bucket,
            templates=self._backend_client.get_templates(team_id=self.team_id).get(
                "data", []
            ),
            validators=self.annotation_validators,
            reporter=self.get_default_reporter(log_info=False, log_warning=False),
            folder_path=folder_path,
        )
        return use_case.execute()

    def upload_image_annotations(
        self,
        project_name: str,
        folder_name: str,
        image_name: str,
        annotations: dict,
        mask: io.BytesIO = None,
        verbose: bool = True,
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)
        try:
            image = self._get_image(project, image_name, folder)
        except AppException:
            raise AppException("There is no images to attach annotation.")
        use_case = usecases.UploadAnnotationUseCase(
            project=project,
            folder=folder,
            images=self.images,
            team=self.team_data,
            annotation_classes=AnnotationClassRepository(
                service=self._backend_client, project=project
            ).get_all(),
            image=image,
            annotations=annotations,
            templates=self._backend_client.get_templates(team_id=self.team_id).get(
                "data", []
            ),
            backend_service_provider=self._backend_client,
            mask=mask,
            verbose=verbose,
            reporter=self.get_default_reporter(),
            validators=self.annotation_validators,
        )
        return use_case.execute()

    def get_model_metrics(self, model_id: int):
        use_case = usecases.GetModelMetricsUseCase(
            model_id=model_id,
            team_id=self.team_id,
            backend_service_provider=self._backend_client,
        )
        return use_case.execute()

    def delete_model(self, model_id: int):
        use_case = usecases.DeleteMLModel(model_id=model_id, models=self.ml_models)
        return use_case.execute()

    def download_export(
        self,
        project_name: str,
        export_name: str,
        folder_path: str,
        extract_zip_contents: bool,
        to_s3_bucket: bool,
    ):
        project = self._get_project(project_name)
        use_case = usecases.DownloadExportUseCase(
            service=self._backend_client,
            project=project,
            export_name=export_name,
            folder_path=folder_path,
            extract_zip_contents=extract_zip_contents,
            to_s3_bucket=to_s3_bucket,
            reporter=self.get_default_reporter(),
        )
        return use_case.execute()

    def download_ml_model(self, model_data: dict, download_path: str):
        model = MLModelEntity(
            uuid=model_data["id"],
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
            backend_service_provider=self._backend_client,
            team_id=self.team_id,
        )
        return use_case.execute()

    def benchmark(
        self,
        project_name: str,
        ground_truth_folder_name: str,
        folder_names: List[str],
        export_root: str,
        image_list: List[str],
        annot_type: str,
        show_plots: bool,
    ):
        project = self._get_project(project_name)
        export_response = self.prepare_export(
            project.name,
            folder_names=folder_names,
            include_fuse=False,
            only_pinned=False,
        )
        if export_response.errors:
            return export_response

        response = usecases.DownloadExportUseCase(
            service=self._backend_client,
            project=project,
            export_name=export_response.data["name"],
            folder_path=export_root,
            extract_zip_contents=True,
            to_s3_bucket=False,
            reporter=self.get_default_reporter(),
        ).execute()
        if response.errors:
            raise AppException(response.errors)
        use_case = usecases.BenchmarkUseCase(
            project=project,
            ground_truth_folder_name=ground_truth_folder_name,
            folder_names=folder_names,
            export_dir=export_root,
            image_list=image_list,
            annotation_type=annot_type,
            show_plots=show_plots,
        )
        return use_case.execute()

    def consensus(
        self,
        project_name: str,
        folder_names: list,
        export_path: str,
        image_list: list,
        annot_type: str,
        show_plots: bool,
    ):
        project = self._get_project(project_name)

        export_response = self.prepare_export(
            project.name,
            folder_names=folder_names,
            include_fuse=False,
            only_pinned=False,
        )
        if export_response.errors:
            return export_response

        response = self.download_export(
            project_name=project.name,
            export_name=export_response.data["name"],
            folder_path=export_path,
            extract_zip_contents=True,
            to_s3_bucket=False,
        )
        if response.errors:
            raise AppException(response.errors)
        use_case = usecases.ConsensusUseCase(
            project=project,
            folder_names=folder_names,
            export_dir=export_path,
            image_list=image_list,
            annotation_type=annot_type,
            show_plots=show_plots,
        )
        return use_case.execute()

    def run_prediction(
        self, project_name: str, images_list: list, model_name: str, folder_name: str
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)
        ml_model_repo = MLModelRepository(
            team_id=project.id, service=self._backend_client
        )
        use_case = usecases.RunPredictionUseCase(
            project=project,
            ml_model_repo=ml_model_repo,
            ml_model_name=model_name,
            images_list=images_list,
            service=self._backend_client,
            folder=folder,
        )
        return use_case.execute()

    def list_images(
        self,
        project_name: str,
        annotation_status: str = None,
        name_prefix: str = None,
    ):
        project = self._get_project(project_name)

        use_case = usecases.GetAllImagesUseCase(
            project=project,
            service_provider=self._backend_client,
            annotation_status=annotation_status,
            name_prefix=name_prefix,
        )
        return use_case.execute()

    def search_models(
        self,
        name: str,
        model_type: str = None,
        project_id: int = None,
        task: str = None,
        include_global: bool = True,
    ):
        ml_models_repo = MLModelRepository(
            service=self._backend_client, team_id=self.team_id
        )
        condition = Condition("team_id", self.team_id, EQ)
        if name:
            condition &= Condition("name", name, EQ)
        if model_type:
            condition &= Condition("type", model_type, EQ)
        if project_id:
            condition &= Condition("project_id", project_id, EQ)
        if task:
            condition &= Condition("task", task, EQ)
        if include_global:
            condition &= Condition("include_global", include_global, EQ)

        use_case = usecases.SearchMLModels(
            ml_models_repo=ml_models_repo, condition=condition
        )
        return use_case.execute()

    def delete_annotations(
        self,
        project_name: str,
        folder_name: str,
        item_names: Optional[List[str]] = None,
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)
        use_case = usecases.DeleteAnnotations(
            project=project,
            folder=folder,
            backend_service=self._backend_client,
            image_names=item_names,
        )
        return use_case.execute()

    @staticmethod
    def validate_annotations(
        project_type: str, annotation: dict, allow_extra: bool = True
    ):
        use_case = usecases.ValidateAnnotationUseCase(
            project_type,
            annotation,
            validators=AnnotationValidators(),
            allow_extra=allow_extra,
        )
        return use_case.execute()

    def add_contributors_to_project(self, project_name: str, emails: list, role: str):
        project = self.get_project_metadata(
            project_name=project_name, include_contributors=True
        )
        use_case = usecases.AddContributorsToProject(
            reporter=self.get_default_reporter(),
            team=self.team,
            project=project.data["project"],
            emails=emails,
            role=role,
            service=self.backend_client,
        )
        return use_case.execute()

    def invite_contributors_to_team(self, emails: list, set_admin: bool):
        use_case = usecases.InviteContributorsToTeam(
            reporter=self.get_default_reporter(),
            team=self.team,
            emails=emails,
            set_admin=set_admin,
            service=self.backend_client,
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
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)

        use_case = usecases.UploadVideosAsImages(
            reporter=self.get_default_reporter(),
            service=self.backend_client,
            project=project,
            folder=folder,
            settings=ProjectSettingsRepository(
                service=self._backend_client, project=project
            ),
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

    def get_annotations(
        self, project_name: str, folder_name: str, item_names: List[str], logging=True
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)
        use_case = usecases.GetAnnotations(
            reporter=self.get_default_reporter(log_info=logging, log_debug=logging),
            project=project,
            folder=folder,
            images=self.images,
            item_names=item_names,
            backend_service_provider=self.backend_client,
        )
        return use_case.execute()

    def get_annotations_per_frame(
        self, project_name: str, folder_name: str, video_name: str, fps: int
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)

        use_case = usecases.GetVideoAnnotationsPerFrame(
            reporter=self.get_default_reporter(),
            project=project,
            folder=folder,
            images=self.images,
            video_name=video_name,
            fps=fps,
            backend_service_provider=self.backend_client,
        )
        return use_case.execute()

    def upload_priority_scores(
        self, project_name, folder_name, scores, project_folder_name
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)
        use_case = usecases.UploadPriorityScoresUseCase(
            reporter=self.get_default_reporter(),
            project=project,
            folder=folder,
            scores=scores,
            backend_service_provider=self.backend_client,
            project_folder_name=project_folder_name,
        )
        return use_case.execute()

    def get_integrations(self):
        team = self.team_data
        use_cae = usecases.GetIntegrations(
            reporter=self.get_default_reporter(),
            team=self.team_data,
            integrations=self.get_integrations_repo(team_id=team.uuid),
        )
        return use_cae.execute()

    def attach_integrations(
        self,
        project_name: str,
        folder_name: str,
        integration: IntegrationEntity,
        folder_path: str,
    ):
        team = self.team_data
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)
        use_case = usecases.AttachIntegrations(
            reporter=self.get_default_reporter(),
            team=self.team_data,
            backend_service=self.backend_client,
            project=project,
            folder=folder,
            integrations=self.get_integrations_repo(team_id=team.uuid),
            integration=integration,
            folder_path=folder_path,
        )
        return use_case.execute()

    def query_entities(
        self, project_name: str, folder_name: str, query: str = None, subset: str = None
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)

        use_case = usecases.QueryEntitiesUseCase(
            reporter=self.get_default_reporter(),
            project=project,
            folder=folder,
            query=query,
            subset=subset,
            backend_service_provider=self.backend_client,
        )
        return use_case.execute()

    def get_item(
        self,
        project_name: str,
        folder_name: str,
        item_name: str,
        include_custom_metadata: bool,
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)
        use_case = usecases.GetItem(
            reporter=self.get_default_reporter(),
            project=project,
            folder=folder,
            item_name=item_name,
            backend_client=self.backend_client,
            include_custom_metadata=include_custom_metadata,
        )
        return use_case.execute()

    def list_items(
        self,
        project_name: str,
        folder_name: str,
        name_contains: str = None,
        annotation_status: str = None,
        annotator_email: str = None,
        qa_email: str = None,
        recursive: bool = False,
        include_custom_metadata: bool = False,
        **kwargs,
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)
        search_condition = Condition.get_empty_condition()
        if name_contains:
            search_condition &= Condition("name", name_contains, EQ)
        if annotation_status:
            search_condition &= Condition(
                "annotation_status",
                constances.AnnotationStatus.get_value(annotation_status),
                EQ,
            )
        if qa_email:
            search_condition &= Condition("qa_id", qa_email, EQ)
        if annotator_email:
            search_condition &= Condition("annotator_id", annotator_email, EQ)

        search_condition &= build_condition(**kwargs)
        use_case = usecases.ListItems(
            reporter=self.get_default_reporter(),
            project=project,
            folder=folder,
            folders=self.folders,
            recursive=recursive,
            backend_client=self.backend_client,
            search_condition=search_condition,
            include_custom_metadata=include_custom_metadata,
        )
        return use_case.execute()

    def attach_items(
        self,
        project_name: str,
        folder_name: str,
        attachments: List[AttachmentEntity],
        annotation_status: str,
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)

        use_case = usecases.AttachItems(
            reporter=self.get_default_reporter(),
            project=project,
            folder=folder,
            attachments=attachments,
            annotation_status=annotation_status,
            backend_service_provider=self.backend_client,
        )
        return use_case.execute()

    def copy_items(
        self,
        project_name: str,
        from_folder: str,
        to_folder: str,
        items: List[str] = None,
        include_annotations: bool = False,
    ):
        project = self._get_project(project_name)
        from_folder = self._get_folder(project, from_folder)
        to_folder = self._get_folder(project, to_folder)

        use_case = usecases.CopyItems(
            self.get_default_reporter(),
            project=project,
            from_folder=from_folder,
            to_folder=to_folder,
            item_names=items,
            items=self.items,
            backend_service_provider=self.backend_client,
            include_annotations=include_annotations,
        )
        return use_case.execute()

    def move_items(
        self,
        project_name: str,
        from_folder: str,
        to_folder: str,
        items: List[str] = None,
    ):
        project = self._get_project(project_name)
        from_folder = self._get_folder(project, from_folder)
        to_folder = self._get_folder(project, to_folder)

        use_case = usecases.MoveItems(
            self.get_default_reporter(),
            project=project,
            from_folder=from_folder,
            to_folder=to_folder,
            item_names=items,
            items=self.items,
            backend_service_provider=self.backend_client,
        )
        return use_case.execute()

    def set_annotation_statuses(
        self,
        project_name: str,
        folder_name: str,
        annotation_status: str,
        item_names: List[str] = None,
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)

        use_case = usecases.SetAnnotationStatues(
            self.get_default_reporter(),
            project=project,
            folder=folder,
            annotation_status=annotation_status,
            item_names=item_names,
            items=self.items,
            backend_service_provider=self.backend_client,
        )
        return use_case.execute()

    def download_annotations(
        self,
        project_name: str,
        folder_name: str,
        destination: str,
        recursive: bool,
        item_names: Optional[List[str]],
        callback: Optional[Callable],
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)

        use_case = usecases.DownloadAnnotations(
            reporter=self.get_default_reporter(),
            project=project,
            folder=folder,
            destination=destination,
            recursive=recursive,
            item_names=item_names,
            items=self.items,
            folders=self.folders,
            classes=AnnotationClassRepository(
                service=self._backend_client, project=project
            ),
            backend_service_provider=self.backend_client,
            callback=callback,
        )
        return use_case.execute()

    def list_subsets(self, project_name: str):
        project = self._get_project(project_name)
        use_case = usecases.ListSubsetsUseCase(
            reporter=self.get_default_reporter(),
            project=project,
            backend_client=self.backend_client,
        )
        return use_case.execute()

    def create_custom_schema(self, project_name: str, schema: dict):
        project = self._get_project(project_name)

        use_case = usecases.CreateCustomSchemaUseCase(
            reporter=self.get_default_reporter(),
            project=project,
            schema=schema,
            backend_client=self.backend_client,
        )
        return use_case.execute()

    def get_custom_schema(self, project_name: str):
        project = self._get_project(project_name)
        use_case = usecases.GetCustomSchemaUseCase(
            reporter=self.get_default_reporter(),
            project=project,
            backend_client=self.backend_client,
        )
        return use_case.execute()

    def delete_custom_schema(self, project_name: str, fields: List[str]):
        project = self._get_project(project_name)
        use_case = usecases.DeleteCustomSchemaUseCase(
            reporter=self.get_default_reporter(),
            project=project,
            fields=fields,
            backend_client=self.backend_client,
        )
        return use_case.execute()

    def upload_custom_values(
        self, project_name: str, folder_name: str, items: List[dict]
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)

        use_case = usecases.UploadCustomValuesUseCase(
            reporter=self.get_default_reporter(),
            project=project,
            folder=folder,
            items=items,
            backend_client=self.backend_client,
        )
        return use_case.execute()

    def delete_custom_values(
        self, project_name: str, folder_name: str, items: List[dict]
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)

        use_case = usecases.DeleteCustomValuesUseCase(
            reporter=self.get_default_reporter(),
            project=project,
            folder=folder,
            items=items,
            backend_client=self.backend_client,
        )
        return use_case.execute()
