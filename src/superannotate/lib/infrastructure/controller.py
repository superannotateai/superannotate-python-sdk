import copy
import io
import tempfile
from functools import cached_property
from functools import lru_cache
from typing import Iterable
from typing import List

import lib.core as constances
from lib.core import usecases
from lib.core.conditions import Condition
from lib.core.conditions import CONDITION_EQ as EQ
from lib.core.entities import AnnotationClassEntity
from lib.core.entities import ConfigEntity
from lib.core.entities import FolderEntity
from lib.core.entities import ImageEntity
from lib.core.entities import MLModelEntity
from lib.core.entities import ProjectEntity
from lib.core.exceptions import AppException
from lib.core.response import Response
from lib.infrastructure.repositories import AnnotationClassRepository
from lib.infrastructure.repositories import ConfigRepository
from lib.infrastructure.repositories import FolderRepository
from lib.infrastructure.repositories import ImageRepository
from lib.infrastructure.repositories import MLModelRepository
from lib.infrastructure.repositories import ProjectRepository
from lib.infrastructure.repositories import ProjectSettingsRepository
from lib.infrastructure.repositories import S3Repository
from lib.infrastructure.repositories import TeamRepository
from lib.infrastructure.repositories import WorkflowRepository
from lib.infrastructure.services import SuperannotateBackendService


class BaseController:
    def __init__(self, logger, config_path=constances.CONFIG_FILE_LOCATION):
        self._config_path = config_path

        token, main_endpoint = (
            self.configs.get_one("token"),
            self.configs.get_one("main_endpoint"),
        )
        if not main_endpoint:
            self.configs.insert(ConfigEntity("main_endpoint", constances.BACKEND_URL))
        if not token:
            self.configs.insert(ConfigEntity("token", ""))
            raise AppException("Fill config.json")

        self._backend_client = SuperannotateBackendService(
            api_url=self.configs.get_one("main_endpoint").value,
            auth_token=ConfigRepository().get_one("token").value,
            logger=logger,
        )
        self._s3_upload_auth_data = None

    def set_token(self, token):
        self.configs.insert(ConfigEntity("token", token))

    @cached_property
    def projects(self):
        return ProjectRepository(self._backend_client)

    @cached_property
    def folders(self):
        return FolderRepository(self._backend_client)

    @cached_property
    def ml_models(self):
        return MLModelRepository(self._backend_client, self.team_id)

    @cached_property
    def teams(self):
        return TeamRepository(self._backend_client)

    @cached_property
    def images(self):
        return ImageRepository(self._backend_client)

    @cached_property
    def configs(self):
        return ConfigRepository(self._config_path)

    @cached_property
    def team_id(self) -> int:
        return int(self.configs.get_one("token").value.split("=")[-1])

    # TODO set timed cache 1 hour with expiration time
    @lru_cache
    def get_auth_data(self, project_id: int, team_id: int, folder_id: int):
        return self._backend_client.get_s3_upload_auth_token(
            team_id, folder_id, project_id
        )

    def get_s3_repository(
        self, team_id: int, project_id: int, folder_id: int, bucket: str = None
    ):
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


class Controller(BaseController):
    def _get_project(self, name: str):
        use_case = usecases.GetProjectByNameUseCase(
            name=name,
            team_id=self.team_id,
            projects=ProjectRepository(service=self._backend_client),
        )
        return use_case.execute().data

    def _get_folder(self, project: ProjectEntity, name: str = None):
        name = self.get_folder_name(name)
        use_case = usecases.GetFolderUseCase(
            project=project,
            folders=self.folders,
            folder_name=name,
            team_id=self.team_id,
        )

        return use_case.execute().data

    @staticmethod
    def get_folder_name(name: str = None):
        if name:
            return name
        return "root"

    def search_project(self, name: str, **kwargs) -> Response:
        condition = Condition("name", name, EQ)
        for key, val in kwargs.items():
            condition = condition & Condition(key, val, EQ)
        use_case = usecases.GetProjectsUseCase(
            condition=condition, projects=self.projects, team_id=self.team_id,
        )
        return use_case.execute()

    def create_project(
        self,
        name: str,
        description: str,
        project_type: str,
        contributors: Iterable = tuple(),
        settings: Iterable = tuple(),
        annotation_classes: Iterable = tuple(),
        workflows: Iterable = tuple(),
    ) -> Response:
        entity = ProjectEntity(
            name=name,
            description=description,
            project_type=constances.ProjectType[project_type.upper()].value,
            team_id=self.team_id,
        )
        use_case = usecases.CreateProjectUseCase(
            project=entity,
            projects=self.projects,
            backend_service_provider=self._backend_client,
            settings_repo=ProjectSettingsRepository,
            workflows_repo=WorkflowRepository,
            annotation_classes_repo=AnnotationClassRepository,
            settings=[
                ProjectSettingsRepository.dict2entity(setting) for setting in settings
            ],
            workflows=[
                WorkflowRepository.dict2entity(workflow) for workflow in workflows
            ],
            annotation_classes=[
                AnnotationClassRepository.dict2entity(annotation_class)
                for annotation_class in annotation_classes
            ],
            contributors=contributors,
        )
        return use_case.execute()

    def delete_project(self, name: str):
        use_case = usecases.DeleteProjectUseCase(
            project_name=name, team_id=self.team_id, projects=self.projects,
        )
        return use_case.execute()

    def update_project(self, name: str, project_data: dict) -> Response:
        entities = self.projects.get_all(
            Condition("team_id", self.team_id, EQ) & Condition("name", name, EQ)
        )
        project = entities[0]
        if entities and len(entities) == 1:
            project.name = project_data["name"]
            use_case = usecases.UpdateProjectUseCase(project, self.projects)
            use_case.execute()
            return use_case.execute()
        raise AppException("There are duplicated names.")

    def upload_images(
        self,
        project_name: str,
        folder_name: str,
        images: List[ImageEntity],
        annotation_status: str = None,
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)
        limit = self.get_auth_data(project.uuid, project.team_id, folder.uuid)[
            "availableImageCount"
        ]

        use_case = usecases.AttachFileUrlsUseCase(
            project=project,
            folder=folder,
            limit=limit,
            backend_service_provider=self._backend_client,
            attachments=images,
            annotation_status=annotation_status,
        )
        return use_case.execute()

    def upload_image_to_s3(
        self,
        project_name: str,
        image_path: str,  # image path to upload
        image_bytes: io.BytesIO,
        folder_name: str = None,  # project folder path
        image_quality_in_editor: str = None,
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)
        s3_repo = self.get_s3_repository(self.team_id, project.uuid, folder.uuid)
        auth_data = self.get_auth_data(project.uuid, self.team_id, folder.uuid)
        use_case = usecases.UploadImageS3UseCas(
            project=project,
            project_settings=ProjectSettingsRepository(self._backend_client, project),
            image_path=image_path,
            image=image_bytes,
            s3_repo=s3_repo,
            upload_path=auth_data["filePath"],
            image_quality_in_editor=image_quality_in_editor,
        )
        use_case.execute()
        return use_case.execute()

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
        project_to_create.name = name
        project_to_create.description = project_description
        use_case = usecases.CloneProjectUseCase(
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

    def attach_urls(
        self,
        project_name: str,
        files: List[ImageEntity],
        folder_name: str = None,
        annotation_status: str = None,
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)
        auth_data = self.get_auth_data(project.uuid, project.team_id, folder.uuid)

        limit = auth_data["availableImageCount"]

        use_case = usecases.AttachFileUrlsUseCase(
            project=project,
            folder=folder,
            attachments=files,
            limit=limit,
            backend_service_provider=self._backend_client,
            annotation_status=annotation_status,
        )
        return use_case.execute()

    def create_folder(self, project: str, folder_name: str):
        project = self._get_project(project)
        folder = FolderEntity(
            name=folder_name, project_id=project.uuid, team_id=project.team_id
        )
        use_case = usecases.CreateFolderUseCase(
            project=project, folder=folder, folders=self.folders,
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

    def search_folder(self, project_name: str, include_users=False, **kwargs):
        condition = None
        if kwargs:
            conditions_iter = iter(kwargs)
            key = next(conditions_iter)
            condition = Condition(key, kwargs[key], EQ)
            for key, val in conditions_iter:
                condition = condition & Condition(key, val, EQ)

        project = self._get_project(project_name)
        use_case = usecases.SearchFolderUseCase(
            project=project,
            folders=self.folders,
            condition=condition,
            include_users=include_users,
        )
        return use_case.execute()

    def get_project_folders(
        self, project_name: str,
    ):
        project = self._get_project(project_name)
        use_case = usecases.GetProjectFoldersUseCase(
            project=project, folders=self.folders,
        )
        return use_case.execute()

    def delete_folders(self, project_name: str, folder_names: List[str]):
        project = self._get_project(project_name)
        folders = self.get_project_folders(project_name).data

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
            backend_service_provider=self._backend_client,
            include_fuse=include_fuse,
            only_pinned=only_pinned,
            annotation_statuses=annotation_statuses,
        )
        return use_case.execute()

    def get_team(self):
        use_case = usecases.GetTeamUseCase(teams=self.teams, team_id=self.team_id)
        return use_case.execute()

    def invite_contributor(self, email: str, is_admin: bool):
        use_case = usecases.InviteContributorUseCase(
            backend_service_provider=self._backend_client,
            email=email,
            team_id=self.team_id,
            is_admin=is_admin,
        )
        return use_case.execute()

    def delete_contributor_invitation(self, email: str):
        team = self.teams.get_one(self.team_id)
        use_case = usecases.DeleteContributorInvitationUseCase(
            backend_service_provider=self._backend_client, email=email, team=team,
        )
        return use_case.execute()

    def search_team_contributors(self, **kwargs):
        condition = None
        if any(kwargs.values()):
            conditions_iter = iter(kwargs)
            key = next(conditions_iter)
            if kwargs[key]:
                condition = Condition(key, kwargs[key], EQ)
                for key, val in conditions_iter:
                    condition = condition & Condition(key, val, EQ)

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
        self, project: ProjectEntity, image_name: str, folder_path: str = None,
    ) -> ImageEntity:
        folder = self._get_folder(project, folder_path)
        use_case = usecases.GetImageUseCase(
            project=project, folder=folder, image_name=image_name, images=self.images,
        )
        return use_case.execute().data

    def get_image(
        self, project_name: str, image_name: str, folder_path: str = None
    ) -> ImageEntity:
        return self._get_image(self._get_project(project_name), image_name, folder_path)

    def update_folder(self, project_name: str, folder_name: str, folder_data: dict):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)
        for field, value in folder_data.items():
            setattr(folder, field, value)
        use_case = usecases.UpdateFolderUseCase(folders=self.folders, folder=folder,)
        return use_case.execute()

    def get_image_bytes(
        self,
        project_name: str,
        image_name: str,
        folder_name: str = None,
        image_variant: str = None,
    ):
        project = self._get_project(project_name)
        image = self._get_image(project, image_name, folder_name)
        use_case = usecases.GetImageBytesUseCase(
            image=image,
            backend_service_provider=self._backend_client,
            image_variant=image_variant,
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
        image = self._get_image(
            from_project, folder_path=from_folder_name, image_name=image_name
        )
        to_project = self._get_project(to_project_name)
        uploaded_image = self._get_image(
            to_project, folder_path=to_folder_name, image_name=image_name
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

    def download_image_from_public_url(
        self, project_name: str, image_url: str, image_name: str = None
    ):
        use_case = usecases.DownloadImageFromPublicUrlUseCase(
            project=self._get_project(project_name),
            image_url=image_url,
            image_name=image_name,
        )
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
        project = self.projects.get_one(
            uuid=self._get_project(project_name).uuid, team_id=self.team_id
        )
        use_case = usecases.GetProjectMetadataUseCase(
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
            workflows=WorkflowRepository(
                service=self._backend_client, project=project_entity
            ),
            annotation_classes=AnnotationClassRepository(
                service=self._backend_client, project=project_entity
            ),
        )
        return use_case.execute()

    def search_annotation_classes(self, project_name: str, name_prefix: str = None):
        project_entity = self._get_project(project_name)
        use_case = usecases.GetAnnotationClassesUseCase(
            classes=AnnotationClassRepository(
                service=self._backend_client, project=project_entity
            ),
            condition=Condition("name", name_prefix, EQ),
        )
        return use_case.execute()

    def set_project_settings(self, project_name: str, new_settings: List[dict]):
        project_entity = self._get_project(project_name)
        use_case = usecases.UpdateSettingsUseCase(
            settings=ProjectSettingsRepository(
                service=self._backend_client, project=project_entity
            ),
            to_update=new_settings,
            backend_service_provider=self._backend_client,
            project_id=project_entity.uuid,
            team_id=project_entity.team_id,
        )
        return use_case.execute()

    def delete_image(self, image_name, project_name):
        image = self.get_image(project_name=project_name, image_name=image_name)
        project_entity = self._get_project(project_name)
        use_case = usecases.DeleteImageUseCase(
            images=ImageRepository(service=self._backend_client),
            image=image,
            team_id=project_entity.team_id,
            project_id=project_entity.uuid,
        )
        return use_case.execute()

    def get_image_metadata(self, project_name: str, folder_name: str, image_name: str):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)
        use_case = usecases.GetImageMetadataUseCase(
            image_name=image_name,
            project=project,
            folder=folder,
            service=self._backend_client,
        )
        return use_case.execute()

    def set_images_annotation_statuses(
        self,
        project_name: str,
        folder_name: str,
        image_names: list,
        annotation_status: str,
    ):
        project_entity = self._get_project(project_name)
        folder_entity = self._get_folder(project_entity, folder_name)
        images_repo = ImageRepository(service=self._backend_client)
        use_case = usecases.SetImageAnnotationStatuses(
            service=self._backend_client,
            image_names=image_names,
            team_id=project_entity.team_id,
            project_id=project_entity.uuid,
            folder_id=folder_entity.uuid,
            images_repo=images_repo,
            annotation_status=constances.AnnotationStatus.get_value(annotation_status),
        )
        return use_case.execute()

    def delete_images(
        self, project_name: str, folder_name: str, image_names: List[str] = None,
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)

        use_case = usecases.DeleteImagesUseCase(
            project=project,
            folder=folder,
            images=self.images,
            image_names=image_names,
            backend_service_provider=self._backend_client,
        )
        return use_case.execute()

    def assign_images(
        self, project_name: str, folder_name: str, image_names: list, user: str
    ):
        project_entity = self._get_project(project_name)
        use_case = usecases.AssignImagesUseCase(
            project_entity=project_entity,
            service=self._backend_client,
            folder_name=folder_name,
            image_names=image_names,
            user=user,
        )
        return use_case.execute()

    def un_assign_images(self, project_name, folder_name, image_names):
        project = self._get_project(project_name)
        folder_name = self.get_folder_name(folder_name)
        use_case = usecases.UnAssignImagesUseCase(
            project_entity=project,
            service=self._backend_client,
            folder_name=folder_name,
            image_names=image_names,
        )
        return use_case.execute()

    def un_assign_folder(self, project_name: str, folder_name: str):
        project_entity = self._get_project(project_name)
        use_case = usecases.UnAssignFolderUseCase(
            service=self._backend_client,
            project_entity=project_entity,
            folder_name=folder_name,
        )
        return use_case.execute()

    def assign_folder(self, project_name: str, folder_name: str, users: List[str]):
        project_entity = self._get_project(project_name)
        use_case = usecases.AssignFolderUseCase(
            service=self._backend_client,
            project_entity=project_entity,
            folder_name=folder_name,
            users=users,
        )
        return use_case.execute()

    def share_project(self, project_name: str, user_id: str, user_role: str):
        project_entity = self._get_project(project_name)
        use_case = usecases.ShareProjectUseCase(
            service=self._backend_client,
            project_entity=project_entity,
            user_id=user_id,
            user_role=user_role,
        )
        use_case.execute()

    def un_share_project(self, project_name: str, user_id: str):
        project_entity = self._get_project(project_name)
        use_case = usecases.UnShareProjectUseCase(
            service=self._backend_client,
            project_entity=project_entity,
            user_id=user_id,
        )
        return use_case.execute()

    @staticmethod
    def download_images_from_google_clout(
        project_name: str, bucket_name: str, folder_name: str, download_path: str
    ):
        use_case = usecases.DownloadGoogleCloudImages(
            project_name=project_name,
            bucket_name=bucket_name,
            folder_name=folder_name,
            download_path=download_path,
        )
        return use_case.execute()

    @staticmethod
    def download_images_from_azure_cloud(
        container_name: str, folder_name: str, download_path: str
    ):
        use_case = usecases.DownloadAzureCloudImages(
            container=container_name,
            folder_name=folder_name,
            download_path=download_path,
        )
        return use_case.execute()

    def get_image_annotations(
        self, project_name: str, folder_name: str, image_name: str
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project=project, name=folder_name)

        use_case = usecases.GetImageAnnotationsUseCase(
            service=self._backend_client,
            project=project,
            folder=folder,
            image_name=image_name,
            images=ImageRepository(service=self._backend_client),
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
        )
        return use_case.execute()

    def download_image_pre_annotations(
        self, project_name: str, folder_name: str, image_name: str, destination: str
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project=project, name=folder_name)

        use_case = usecases.DownloadImagePreAnnotationsUseCase(
            service=self._backend_client,
            project=project,
            folder=folder,
            image_name=image_name,
            images=ImageRepository(service=self._backend_client),
            destination=destination,
        )
        return use_case.execute()

    @staticmethod
    def get_image_from_s3(s3_bucket, image_path: str):
        use_case = usecases.GetS3ImageUseCase(
            s3_bucket=s3_bucket, image_path=image_path
        )
        use_case.execute()
        return use_case.execute()

    def get_image_pre_annotations(
        self, project_name: str, folder_name: str, image_name: str
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project=project, name=folder_name)

        use_case = usecases.GetImagePreAnnotationsUseCase(
            service=self._backend_client,
            project=project,
            folder=folder,
            image_name=image_name,
            images=ImageRepository(service=self._backend_client),
        )
        use_case.execute()
        return use_case.execute()

    def get_exports(self, project_name: str, return_metadata: bool):
        project = self._get_project(project_name)

        use_case = usecases.GetExportsUseCase(
            service=self._backend_client,
            project=project,
            return_metadata=return_metadata,
        )
        return use_case.execute()

    def backend_upload_from_s3(
        self,
        project_name: str,
        folder_name: str,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        folder_path: str,
        image_quality: str,
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)
        use_case = usecases.UploadS3ImagesBackendUseCase(
            backend_service_provider=self._backend_client,
            project=project,
            settings=ProjectSettingsRepository(self._backend_client, project),
            folder=folder,
            access_key=access_key,
            secret_key=secret_key,
            bucket_name=bucket_name,
            folder_path=folder_path,
            image_quality=image_quality,
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

    def extract_video_frames(
        self,
        project_name: str,
        folder_name: str,
        video_path: str,
        extract_path: str,
        start_time: float,
        end_time: float = None,
        target_fps: float = None,
        annotation_status: str = None,
        image_quality_in_editor: str = None,
        limit: int = None,
    ):
        annotation_status_code = (
            constances.AnnotationStatus.get_value(annotation_status)
            if annotation_status
            else None
        )
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)
        use_case = usecases.ExtractFramesUseCase(
            backend_service_provider=self._backend_client,
            project=project,
            folder=folder,
            video_path=video_path,
            extract_path=extract_path,
            start_time=start_time,
            end_time=end_time,
            target_fps=target_fps,
            annotation_status_code=annotation_status_code,
            image_quality_in_editor=image_quality_in_editor,
            limit=limit,
        )
        return use_case.execute()

    def create_annotation_class(
        self, project_name: str, name: str, color: str, attribute_groups: List[dict]
    ):
        project = self._get_project(project_name)
        annotation_classes = AnnotationClassRepository(
            project=project, service=self._backend_client
        )
        annotation_class = AnnotationClassEntity(
            name=name, color=color, attribute_groups=attribute_groups
        )
        use_case = usecases.CreateAnnotationClassUseCase(
            annotation_classes=annotation_classes, annotation_class=annotation_class,
        )
        use_case.execute()
        return use_case.execute()

    def delete_annotation_class(self, project_name: str, annotation_class_name: str):
        project = self._get_project(project_name)
        use_case = usecases.DeleteAnnotationClassUseCase(
            annotation_class_name=annotation_class_name,
            annotation_classes_repo=AnnotationClassRepository(
                service=self._backend_client, project=project,
            ),
        )
        return use_case.execute()

    def get_annotation_class(self, project_name: str, annotation_class_name: str):
        project = self._get_project(project_name)
        use_case = usecases.GetAnnotationClassUseCase(
            annotation_class_name=annotation_class_name,
            annotation_classes_repo=AnnotationClassRepository(
                service=self._backend_client, project=project,
            ),
        )
        return use_case.execute()

    def download_annotation_classes(self, project_name: str, download_path: str):
        project = self._get_project(project_name)
        use_case = usecases.DownloadAnnotationClassesUseCase(
            annotation_classes_repo=AnnotationClassRepository(
                service=self._backend_client, project=project,
            ),
            download_path=download_path,
        )
        return use_case.execute()

    def create_annotation_classes(self, project_name: str, annotation_classes: list):
        project = self._get_project(project_name)

        use_case = usecases.CreateAnnotationClassesUseCase(
            service=self._backend_client,
            annotation_classes_repo=AnnotationClassRepository(
                service=self._backend_client, project=project,
            ),
            annotation_classes=annotation_classes,
            project=project,
        )
        return use_case.execute()

    @staticmethod
    def create_fuse_image(
        project_type: str,
        image_path: str,
        annotation_classes: List,
        in_memory: bool,
        generate_overlay: bool,
    ):
        use_case = usecases.CreateFuseImageUseCase(
            project_type=project_type,
            image_path=image_path,
            classes=annotation_classes,
            in_memory=in_memory,
            generate_overlay=generate_overlay,
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
        image = self._get_image(project, image_name, folder_name)

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
        folder_path: str,
        annotation_paths: List[str],
        client_s3_bucket=None,
        is_pre_annotations: bool = False,
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)
        use_case = usecases.UploadAnnotationsUseCase(
            project=project,
            folder=folder,
            folder_path=folder_path,
            annotation_paths=annotation_paths,
            backend_service_provider=self._backend_client,
            annotation_classes=AnnotationClassRepository(
                service=self._backend_client, project=project
            ),
            pre_annotation=is_pre_annotations,
            client_s3_bucket=client_s3_bucket,
        )
        return use_case.execute()

    def upload_image_annotations(
        self,
        project_name: str,
        folder_name: str,
        image_name: str,
        annotations: dict,
        mask: io.BytesIO = None,
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)
        use_case = usecases.UploadImageAnnotationsUseCase(
            project=project,
            folder=folder,
            annotation_classes=AnnotationClassRepository(
                service=self._backend_client, project=project
            ),
            image_name=image_name,
            annotations=annotations,
            backend_service_provider=self._backend_client,
            mask=mask,
        )
        return use_case.execute()

    def create_model(
        self,
        model_name: str,
        model_description: str,
        task: str,
        base_model_name: str,
        train_data_paths: List[str],
        test_data_paths: List[str],
        hyper_parameters: dict,
    ):
        use_case = usecases.CreateModelUseCase(
            base_model_name=base_model_name,
            model_name=model_name,
            model_description=model_description,
            task=task,
            team_id=self.team_id,
            backend_service_provider=self._backend_client,
            projects=self.projects,
            folders=self.folders,
            ml_models=self.ml_models,
            train_data_paths=train_data_paths,
            test_data_paths=test_data_paths,
            hyper_parameters=hyper_parameters,
        )
        return use_case.execute()

    def get_model_metrics(self, model_id: int):
        use_case = usecases.GetModelMetricsUseCase(
            model_id=model_id,
            team_id=self.team_id,
            backend_service_provider=self._backend_client,
        )
        return use_case.execute()

    def update_model_status(self, model_id: int, status: int):
        model = MLModelEntity(uuid=model_id, training_status=status)
        use_case = usecases.UpdateModelUseCase(model=model, models=self.ml_models)
        return use_case.execute()

    def delete_model(self, model_id: int):
        use_case = usecases.DeleteMLModel(model_id=model_id, models=self.ml_models)
        return use_case.execute()

    def stop_model_training(self, model_id: int):

        use_case = usecases.StopModelTraining(
            model_id=model_id,
            team_id=self.team_id,
            backend_service_provider=self._backend_client,
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
        project = self._get_project(project_name)
        use_case = usecases.DownloadExportUseCase(
            service=self._backend_client,
            project=project,
            export_name=export_name,
            folder_path=folder_path,
            extract_zip_contents=extract_zip_contents,
            to_s3_bucket=to_s3_bucket,
        )
        return use_case.execute()

    def download_ml_model(self, model_data: dict, download_path: str):
        model = MLModelEntity(
            uuid=model_data["id"],
            path=model_data["path"],
            config_path=model_data["config_path"],
            team_id=model_data["team_id"],
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
        if export_root is None:
            with tempfile.TemporaryDirectory() as export_dir:
                # TODO fix prepare_export & download_export calls
                export = self.prepare_export(project.name)
                self.download_export(
                    project_name=project.name,
                    export_name=export["name"],
                    folder_path=export_dir,
                )
        use_case = usecases.BenchmarkUseCase(
            project=project,
            ground_truth_folder_name=ground_truth_folder_name,
            folder_names=folder_names,
            export_dir=export_dir,
            image_list=image_list,
            annotation_type=annot_type,
            show_plots=show_plots,
        )
        return use_case.execute()

    def consensus(
        self,
        project_name: str,
        folder_names: list,
        export_root: str,
        image_list: list,
        annot_type: str,
        show_plots: bool,
    ):
        project = self._get_project(project_name)
        if export_root is None:
            with tempfile.TemporaryDirectory() as export_dir:
                export = self.prepare_export(project.name)
                self.download_export(
                    project_name=project.name,
                    export_name=export["name"],
                    folder_path=export_dir,
                )
        use_case = usecases.ConsensusUseCase(
            project=project,
            folder_names=folder_names,
            export_dir=export_dir,
            image_list=image_list,
            annotation_type=annot_type,
            show_plots=show_plots,
        )
        return use_case.execute()

    def run_segmentation(
        self, project_name: str, images_list: list, model_name: str, folder_name: str
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)
        ml_model_repo = MLModelRepository(
            team_id=project.uuid, service=self._backend_client
        )
        use_case = usecases.RunSegmentationUseCase(
            project=project,
            ml_model_repo=ml_model_repo,
            ml_model_name=model_name,
            images_list=images_list,
            service=self._backend_client,
            folder=folder,
        )
        return use_case.execute()

    def run_prediction(
        self, project_name: str, images_list: list, model_name: str, folder_name: str
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)
        ml_model_repo = MLModelRepository(
            team_id=project.uuid, service=self._backend_client
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
        self, project_name: str, annotation_status: str = None, name_prefix: str = None,
    ):
        project = self._get_project(project_name)

        use_case = usecases.GetAllImagesUseCase(
            project=project,
            service_provider=self._backend_client,
            annotation_status=annotation_status,
            name_prefix=name_prefix,
        )
        return use_case.execute()

    def upload_file_to_s3(self, to_s3_bucket, path, s3_key: str):
        use_case = usecases.UploadFileToS3UseCase(
            to_s3_bucket=to_s3_bucket, path=path, s3_key=s3_key
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