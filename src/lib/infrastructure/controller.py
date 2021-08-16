import copy
import io
import tempfile
from functools import cached_property
from functools import lru_cache
from typing import Iterable
from typing import List

import lib.core as constances
from src.lib.core import usecases
from src.lib.core.conditions import Condition
from src.lib.core.conditions import CONDITION_EQ as EQ
from src.lib.core.entities import AnnotationClassEntity
from src.lib.core.entities import FolderEntity
from src.lib.core.entities import ImageEntity
from src.lib.core.entities import MLModelEntity
from src.lib.core.entities import ProjectEntity
from src.lib.core.exceptions import AppException
from src.lib.core.response import Response
from src.lib.infrastructure.repositories import AnnotationClassRepository
from src.lib.infrastructure.repositories import ConfigRepository
from src.lib.infrastructure.repositories import FolderRepository
from src.lib.infrastructure.repositories import ImageRepository
from src.lib.infrastructure.repositories import MLModelRepository
from src.lib.infrastructure.repositories import ProjectRepository
from src.lib.infrastructure.repositories import ProjectSettingsRepository
from src.lib.infrastructure.repositories import S3Repository
from src.lib.infrastructure.repositories import TeamRepository
from src.lib.infrastructure.repositories import WorkflowRepository
from src.lib.infrastructure.services import SuperannotateBackendService


class BaseController:
    def __init__(self, backend_client: SuperannotateBackendService, response: Response):
        self._backend_client = backend_client
        self._s3_upload_auth_data = None
        self._response = response

    @property
    def response(self):
        self._response = Response()
        return self._response

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
        return ConfigRepository()

    @cached_property
    def team_id(self) -> int:
        return int(self.configs.get_one("token").value.split("=")[-1])

    # todo set timed cache 1 hour with expiration time
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
        response = Response()
        use_case = usecases.GetProjectByNameUseCase(
            response=response,
            name=name,
            team_id=self.team_id,
            projects=ProjectRepository(service=self._backend_client),
        )
        use_case.execute()
        return response.data

    def _get_folder(self, project: ProjectEntity, name: str = None):
        response = Response()
        name = self.get_folder_name(name)
        use_case = usecases.GetFolderUseCase(
            response=response, project=project, folders=self.folders, folder_name=name,
        )
        use_case.execute()
        return response.data

    @staticmethod
    def get_folder_name(name: str = None):
        if name:
            return name
        return "root"

    def search_project(self, name: str, **kwargs) -> Response:
        condition = Condition("name", name, EQ)
        for key, val in kwargs.items():
            condition = condition & Condition(key, val, EQ)
        response = self.response
        use_case = usecases.GetProjectsUseCase(
            response=response,
            condition=condition,
            projects=self.projects,
            team_id=self.team_id,
        )
        use_case.execute()
        return response

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
            response=self.response,
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
        use_case.execute()
        return self._response

    def delete_project(self, name: str):
        use_case = usecases.DeleteProjectUseCase(
            response=self.response,
            project_name=name,
            team_id=self.team_id,
            projects=self.projects,
        )
        use_case.execute()
        return self._response

    def update_project(self, name: str, project_data: dict) -> Response:
        entities = self.projects.get_all(
            Condition("team_id", self.team_id, EQ) & Condition("name", name, EQ)
        )
        project = entities[0]
        if entities and len(entities) == 1:
            project.name = project_data["name"]
            use_case = usecases.UpdateProjectUseCase(
                self.response, project, self.projects
            )
            use_case.execute()
            return self._response
        raise AppException("There are duplicated names.")

    def upload_images(
        self,
        project_name: str,
        folder_name: str,
        images: List[ImageEntity],
        annotation_status: str = None,
        image_quality: str = None,
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)
        use_case = usecases.AttachImagesUseCase(
            response=self.response,
            project=project,
            folder=folder,
            project_settings=ProjectSettingsRepository(self._backend_client, project),
            backend_service_provider=self._backend_client,
            images=images,
            annotation_status=annotation_status,
            image_quality=image_quality,
        )
        use_case.execute()
        return self._response

    def upload_image_to_s3(
        self,
        project_name: str,
        image_path: str,  # image path to upload
        image_bytes: io.BytesIO,
        folder_name: str = None,  # project folder path
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)
        s3_repo = self.get_s3_repository(self.team_id, project.uuid, folder.uuid)
        auth_data = self.get_auth_data(project.uuid, self.team_id, folder.uuid)
        use_case = usecases.UploadImageS3UseCas(
            response=self.response,
            project=project,
            project_settings=ProjectSettingsRepository(self._backend_client, project),
            image_path=image_path,
            image=image_bytes,
            s3_repo=s3_repo,
            upload_path=auth_data["filePath"],
        )
        use_case.execute()
        return self._response

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
            response=self.response,
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
        use_case.execute()
        return self._response

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
            response=self.response,
            project=project,
            folder=folder,
            attachments=files,
            limit=limit,
            backend_service_provider=self._backend_client,
            annotation_status=annotation_status,
        )
        use_case.execute()
        return self._response

    def create_folder(self, project: str, folder_name: str):
        project = self._get_project(project)
        folder = FolderEntity(
            name=folder_name, project_id=project.uuid, team_id=project.team_id
        )
        use_case = usecases.CreateFolderUseCase(
            response=self.response,
            project=project,
            folder=folder,
            folders=self.folders,
        )
        use_case.execute()
        return self._response

    def get_folder(self, project_name: str, folder_name: str):
        project = self._get_project(project_name)
        use_case = usecases.GetFolderUseCase(
            response=self.response,
            project=project,
            folders=self.folders,
            folder_name=folder_name,
        )
        use_case.execute()
        return self._response

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
            response=self.response,
            project=project,
            folders=self.folders,
            condition=condition,
            include_users=include_users,
        )
        use_case.execute()
        return self._response

    def get_project_folders(
        self, project_name: str,
    ):
        project = self._get_project(project_name)
        use_case = usecases.GetProjectFoldersUseCase(
            response=self.response, project=project, folders=self.folders,
        )
        use_case.execute()
        return self._response

    def delete_folders(self, project_name: str, folder_names: List[str]):
        project = self._get_project(project_name)
        folders = self.get_project_folders(project_name).data

        use_case = usecases.DeleteFolderUseCase(
            response=self.response,
            project=project,
            folders=self.folders,
            folders_to_delete=[
                folder for folder in folders if folder.name in folder_names
            ],
        )
        use_case.execute()
        return self._response

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
            response=self.response,
            project=project,
            folder_names=folder_names,
            backend_service_provider=self._backend_client,
            include_fuse=include_fuse,
            only_pinned=only_pinned,
            annotation_statuses=annotation_statuses,
        )
        use_case.execute()

        return self._response

    def get_team(self):
        use_case = usecases.GetTeamUseCase(
            response=self.response, teams=self.teams, team_id=self.team_id
        )
        use_case.execute()
        return self._response

    def invite_contributor(self, email: str, is_admin: bool):
        use_case = usecases.InviteContributorUseCase(
            response=self.response,
            backend_service_provider=self._backend_client,
            email=email,
            team_id=self.team_id,
            is_admin=is_admin,
        )
        use_case.execute()
        return self._response

    def delete_contributor_invitation(self, email: str):
        team = self.teams.get_one(self.team_id)
        use_case = usecases.DeleteContributorInvitationUseCase(
            response=self.response,
            backend_service_provider=self._backend_client,
            email=email,
            team=team,
        )
        use_case.execute()
        return self._response

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
            response=self.response,
            backend_service_provider=self._backend_client,
            team_id=self.team_id,
            condition=condition,
        )
        use_case.execute()
        return self._response

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
            response=self.response,
            project=project,
            folder=folder,
            images=self.images,
            annotation_status=annotation_status,
            image_name_prefix=image_name_prefix,
        )
        use_case.execute()
        return self._response

    def _get_image(
        self, project: ProjectEntity, image_name: str, folder_path: str = None,
    ) -> ImageEntity:
        response = Response()
        folder = self._get_folder(project, folder_path)
        use_case = usecases.GetImageUseCase(
            response=response,
            project=project,
            folder=folder,
            image_name=image_name,
            images=self.images,
        )
        use_case.execute()
        return response.data

    def get_image(
        self, project_name: str, image_name: str, folder_path: str = None
    ) -> ImageEntity:
        return self._get_image(self._get_project(project_name), image_name, folder_path)

    def update_folder(self, project_name: str, folder_name: str, folder_data: dict):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)
        for field, value in folder_data.items():
            setattr(folder, field, value)
        use_case = usecases.UpdateFolderUseCase(
            response=self.response, folders=self.folders, folder=folder,
        )
        use_case.execute()
        return self._response

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
            response=self.response,
            image=image,
            backend_service_provider=self._backend_client,
            image_variant=image_variant,
        )
        use_case.execute()
        return self._response

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
            response=self.response,
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
        use_case.execute()

    def update_image(
        self, project_name: str, image_name: str, folder_name: str = None, **kwargs
    ):
        image = self.get_image(
            project_name=project_name, image_name=image_name, folder_path=folder_name
        )
        for item, val in kwargs.items():
            setattr(image, item, val)
        use_case = usecases.UpdateImageUseCase(
            response=self.response, image=image, images=self.images
        )
        use_case.execute()

    def download_image_from_public_url(
        self, project_name: str, image_url: str, image_name: str = None
    ):
        response = Response()
        use_case = usecases.DownloadImageFromPublicUrlUseCase(
            response=response,
            project=self._get_project(project_name),
            image_url=image_url,
            image_name=image_name,
        )
        use_case.execute()
        return response

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
            response=self.response,
            project=project,
            from_folder=from_folder,
            to_folder=to_folder,
            image_names=image_names,
            backend_service_provider=self._backend_client,
            include_annotations=include_annotations,
            include_pin=include_pin,
        )
        use_case.execute()
        return self._response

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
            response=self.response,
            project=project,
            from_folder=from_folder,
            to_folder=to_folder,
            image_names=image_names,
            backend_service_provider=self._backend_client,
        )
        use_case.execute()
        return self._response

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
            response=self.response,
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
        use_case.execute()
        return self._response

    def get_project_settings(self, project_name: str):
        project_entity = self._get_project(project_name)
        settings_use_case = usecases.GetSettingsUseCase(
            response=self.response,
            settings=ProjectSettingsRepository(
                service=self._backend_client, project=project_entity
            ),
        )
        settings_use_case.execute()
        return self._response

    def get_project_workflow(self, project_name: str):
        project_entity = self._get_project(project_name)
        workflows_use_case = usecases.GetWorkflowsUseCase(
            workflows=WorkflowRepository(
                service=self._backend_client, project=project_entity
            ),
            annotation_classes=AnnotationClassRepository(
                service=self._backend_client, project=project_entity
            ),
            response=self.response,
        )
        workflows_use_case.execute()
        return self._response

    def search_annotation_classes(self, project_name: str, name_prefix: str = None):
        project_entity = self._get_project(project_name)
        annotation_classes_use_case = usecases.GetAnnotationClassesUseCase(
            response=self.response,
            classes=AnnotationClassRepository(
                service=self._backend_client, project=project_entity
            ),
            condition=Condition("name", name_prefix, EQ),
        )
        annotation_classes_use_case.execute()
        return self._response

    def set_project_settings(self, project_name: str, new_settings: List[dict]):
        project_entity = self._get_project(project_name)
        new_settings_response = Response()
        update_settings_use_case = usecases.UpdateSettingsUseCase(
            response=new_settings_response,
            settings=ProjectSettingsRepository(
                service=self._backend_client, project=project_entity
            ),
            to_update=new_settings,
            backend_service_provider=self._backend_client,
            project_id=project_entity.uuid,
            team_id=project_entity.team_id,
        )
        update_settings_use_case.execute()

        return new_settings_response

    def delete_image(self, image_name, project_name):
        image = self.get_image(project_name=project_name, image_name=image_name)
        project_entity = self._get_project(project_name)
        delete_image_user_case = usecases.DeleteImageUseCase(
            response=self.response,
            images=ImageRepository(service=self._backend_client),
            image=image,
            team_id=project_entity.team_id,
            project_id=project_entity.uuid,
        )
        delete_image_user_case.execute()
        return self._response

    def get_image_metadata(self, project_name: str, folder_name: str, image_name: str):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)
        use_case = usecases.GetImageMetadataUseCase(
            response=self.response,
            image_name=image_name,
            project=project,
            folder=folder,
            service=self._backend_client,
        )
        use_case.execute()
        return self._response

    def set_images_annotation_statuses(
        self,
        project_name: str,
        folder_name: str,
        image_names: list,
        annotation_status: str,
    ):
        project_entity = self._get_project(project_name)
        folder_entity = self._get_folder(project_entity, folder_name)
        set_images_annotation_statuses_use_case = usecases.SetImageAnnotationStatuses(
            response=self._response,
            service=self._backend_client,
            image_names=image_names,
            team_id=project_entity.team_id,
            project_id=project_entity.uuid,
            folder_id=folder_entity.uuid,
            annotation_status=constances.AnnotationStatus.get_value(annotation_status),
        )
        set_images_annotation_statuses_use_case.execute()
        return self._response

    def delete_images(
        self, project_name: str, folder_name: str, image_names: List[str] = None,
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)

        use_case = usecases.DeleteImagesUseCase(
            response=self.response,
            project=project,
            folder=folder,
            images=self.images,
            image_names=image_names,
            backend_service_provider=self._backend_client,
        )
        use_case.execute()
        return self._response

    def assign_images(
        self, project_name: str, folder_name: str, image_names: list, user: str
    ):
        project_entity = self._get_project(project_name)
        assign_images_use_case = usecases.AssignImagesUseCase(
            response=self.response,
            project_entity=project_entity,
            service=self._backend_client,
            folder_name=folder_name,
            image_names=image_names,
            user=user,
        )
        assign_images_use_case.execute()

    def un_assign_images(self, project_name, folder_name, image_names):
        project = self._get_project(project_name)
        folder_name = self.get_folder_name(folder_name)
        use_case = usecases.UnAssignImagesUseCase(
            response=self.response,
            project_entity=project,
            service=self._backend_client,
            folder_name=folder_name,
            image_names=image_names,
        )
        use_case.execute()

    def un_assign_folder(self, project_name: str, folder_name: str):
        project_entity = self._get_project(project_name)
        use_case = usecases.UnAssignFolderUseCase(
            response=self.response,
            service=self._backend_client,
            project_entity=project_entity,
            folder_name=folder_name,
        )
        use_case.execute()

    def assign_folder(self, project_name: str, folder_name: str, users: List[str]):
        project_entity = self._get_project(project_name)
        use_case = usecases.AssignFolderUseCase(
            response=self.response,
            service=self._backend_client,
            project_entity=project_entity,
            folder_name=folder_name,
            users=users,
        )
        use_case.execute()

    def share_project(self, project_name: str, user_id: str, user_role: str):
        project_entity = self._get_project(project_name)
        share_project_use_case = usecases.ShareProjectUseCase(
            response=self.response,
            service=self._backend_client,
            project_entity=project_entity,
            user_id=user_id,
            user_role=user_role,
        )
        share_project_use_case.execute()

    def un_share_project(self, project_name: str, user_id: str):
        project_entity = self._get_project(project_name)
        use_case = usecases.UnShareProjectUseCase(
            response=self.response,
            service=self._backend_client,
            project_entity=project_entity,
            user_id=user_id,
        )
        use_case.execute()

    def download_images_from_google_clout(
        self, project_name: str, bucket_name: str, folder_name: str, download_path: str
    ):
        use_case = usecases.DownloadGoogleCloudImages(
            response=self.response,
            project_name=project_name,
            bucket_name=bucket_name,
            folder_name=folder_name,
            download_path=download_path,
        )
        use_case.execute()
        return self._response

    def download_images_from_azure_cloud(
        self, container_name: str, folder_name: str, download_path: str
    ):
        use_case = usecases.DownloadAzureCloudImages(
            response=self.response,
            container=container_name,
            folder_name=folder_name,
            download_path=download_path,
        )
        use_case.execute()
        return self._response

    def get_image_annotations(
        self, project_name: str, folder_name: str, image_name: str
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project=project, name=folder_name)

        user_case = usecases.GetImageAnnotationsUseCase(
            response=self.response,
            service=self._backend_client,
            project=project,
            folder=folder,
            image_name=image_name,
            images=ImageRepository(service=self._backend_client),
        )
        user_case.execute()
        return self._response

    def download_image_annotations(
        self, project_name: str, folder_name: str, image_name: str, destination: str
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project=project, name=folder_name)
        user_case = usecases.DownloadImageAnnotationsUseCase(
            response=self.response,
            service=self._backend_client,
            project=project,
            folder=folder,
            image_name=image_name,
            images=ImageRepository(service=self._backend_client),
            destination=destination,
        )
        user_case.execute()
        return self._response

    def download_image_pre_annotations(
        self, project_name: str, folder_name: str, image_name: str, destination: str
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project=project, name=folder_name)
        response = self.response
        user_case = usecases.DownloadImagePreAnnotationsUseCase(
            response=response,
            service=self._backend_client,
            project=project,
            folder=folder,
            image_name=image_name,
            images=ImageRepository(service=self._backend_client),
            destination=destination,
        )
        user_case.execute()
        return response

    def get_image_from_s3(self, s3_bucket, image_path: str):
        response = self.response
        use_case = usecases.GetS3ImageUseCase(
            response=response, s3_bucket=s3_bucket, image_path=image_path
        )
        use_case.execute()
        return response

    def get_image_pre_annotations(
        self, project_name: str, folder_name: str, image_name: str
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project=project, name=folder_name)

        user_case = usecases.GetImagePreAnnotationsUseCase(
            response=self.response,
            service=self._backend_client,
            project=project,
            folder=folder,
            image_name=image_name,
            images=ImageRepository(service=self._backend_client),
        )
        user_case.execute()
        return self._response

    def get_exports(self, project_name: str, return_metadata: bool):
        project = self._get_project(project_name)

        use_case = usecases.GetExportsUseCase(
            response=self.response,
            service=self._backend_client,
            project=project,
            return_metadata=return_metadata,
        )
        use_case.execute()

        return self._response

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
            response=self.response,
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
        use_case.execute()
        return self._response

    def get_project_image_count(
        self, project_name: str, folder_name: str, with_all_subfolders: bool
    ):

        project = self._get_project(project_name)
        folder = self._get_folder(project=project, name=folder_name)

        use_case = usecases.GetProjectImageCountUseCase(
            response=self.response,
            service=self._backend_client,
            project=project,
            folder=folder,
            with_all_subfolders=with_all_subfolders,
        )

        use_case.execute()
        return self._response

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
            response=self.response,
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
        use_case.execute()
        return self._response

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
            response=self.response,
            annotation_classes=annotation_classes,
            annotation_class=annotation_class,
        )
        use_case.execute()
        return self._response

    def delete_annotation_class(self, project_name: str, annotation_class_name: str):
        project = self._get_project(project_name)
        use_case = usecases.DeleteAnnotationClassUseCase(
            response=self.response,
            annotation_class_name=annotation_class_name,
            annotation_classes_repo=AnnotationClassRepository(
                service=self._backend_client, project=project,
            ),
        )
        use_case.execute()

    def get_annotation_class(self, project_name: str, annotation_class_name: str):
        project = self._get_project(project_name)
        use_case = usecases.GetAnnotationClassUseCase(
            response=self.response,
            annotation_class_name=annotation_class_name,
            annotation_classes_repo=AnnotationClassRepository(
                service=self._backend_client, project=project,
            ),
        )
        use_case.execute()
        return self._response

    def download_annotation_classes(self, project_name: str, download_path: str):
        project = self._get_project(project_name)
        use_case = usecases.DownloadAnnotationClassesUseCase(
            response=self.response,
            annotation_classes_repo=AnnotationClassRepository(
                service=self._backend_client, project=project,
            ),
            download_path=download_path,
        )
        use_case.execute()
        return self._response

    def create_annotation_classes(self, project_name: str, annotation_classes: list):
        project = self._get_project(project_name)

        use_case = usecases.CreateAnnotationClassesUseCase(
            response=self.response,
            service=self._backend_client,
            annotation_classes_repo=AnnotationClassRepository(
                service=self._backend_client, project=project,
            ),
            annotation_classes=annotation_classes,
            project=project,
        )
        use_case.execute()
        return self._response

    def create_fuse_image(
        self,
        project_type: str,
        image_path: str,
        annotation_classes: List,
        in_memory: bool,
        generate_overlay: bool,
    ):

        use_case = usecases.CreateFuseImageUseCase(
            response=self.response,
            project_type=project_type,
            image_path=image_path,
            classes=annotation_classes,
            in_memory=in_memory,
            generate_overlay=generate_overlay,
        )
        use_case.execute()
        return self._response

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
            response=self.response,
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
        use_case.execute()
        return self._response

    def set_project_workflow(self, project_name: str, steps: list):
        project = self._get_project(project_name)
        use_case = usecases.SetWorkflowUseCase(
            response=self.response,
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
        use_case.execute()

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
            response=self.response,
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
        use_case.execute()
        return self._response

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
            response=self.response,
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
        use_case.execute()

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
            response=self.response,
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
        use_case.execute()
        return self._response

    def get_model_metrics(self, model_id: int):
        use_case = usecases.GetModelMetricsUseCase(
            response=self.response,
            model_id=model_id,
            team_id=self.team_id,
            backend_service_provider=self._backend_client,
        )
        use_case.execute()
        return self._response

    def update_model_status(self, model_id: int, status: int):
        model = MLModelEntity(uuid=model_id, training_status=status)
        use_case = usecases.UpdateModelUseCase(
            response=self.response, model=model, models=self.ml_models
        )
        use_case.execute()
        return self._response

    def delete_model(self, model_id: int):
        use_case = usecases.DeleteMLModel(
            response=self.response, model_id=model_id, models=self.ml_models
        )
        use_case.execute()

    def stop_model_training(self, model_id: int):

        use_case = usecases.StopModelTraining(
            response=self.response,
            model_id=model_id,
            team_id=self.team_id,
            backend_service_provider=self._backend_client,
        )
        use_case.execute()
        return self._response

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
            response=self.response,
            service=self._backend_client,
            project=project,
            export_name=export_name,
            folder_path=folder_path,
            extract_zip_contents=extract_zip_contents,
            to_s3_bucket=to_s3_bucket,
        )
        use_case.execute()
        return self._response

    def download_ml_model(self, model_data: dict, download_path: str):
        model = MLModelEntity(
            uuid=model_data["id"],
            path=model_data["path"],
            config_path=model_data["config_path"],
            team_id=model_data["team_id"],
        )
        use_case = usecases.DownloadMLModelUseCase(
            response=self.response,
            model=model,
            download_path=download_path,
            backend_service_provider=self._backend_client,
            team_id=self.team_id,
        )
        use_case.execute()
        return self._response

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
                # todo fix prepare_export & download_export calls
                export = self.prepare_export(project.name)
                self.download_export(
                    project_name=project.name,
                    export_name=export["name"],
                    folder_path=export_dir,
                )
        use_case = usecases.BenchmarkUseCase(
            response=self.response,
            project=project,
            ground_truth_folder_name=ground_truth_folder_name,
            folder_names=folder_names,
            export_dir=export_dir,
            image_list=image_list,
            annot_type=annot_type,
            show_plots=show_plots,
        )
        use_case.execute()
        return self.response

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
            response=self.response,
            project=project,
            folder_names=folder_names,
            export_dir=export_dir,
            image_list=image_list,
            annot_type=annot_type,
            show_plots=show_plots,
        )
        use_case.execute()
        return self.response

    def run_segmentation(
        self, project_name: str, images_list: list, model_name: str, folder_name: str
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)
        ml_model_repo = MLModelRepository(
            team_id=project.uuid, service=self._backend_client
        )
        use_case = usecases.RunSegmentationUseCase(
            response=self.response,
            project=project,
            ml_model_repo=ml_model_repo,
            ml_model_name=model_name,
            images_list=images_list,
            service=self._backend_client,
            folder=folder,
        )
        use_case.execute()
        return self._response

    def run_prediction(
        self, project_name: str, images_list: list, model_name: str, folder_name: str
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)
        ml_model_repo = MLModelRepository(
            team_id=project.uuid, service=self._backend_client
        )
        use_case = usecases.RunPredictionUseCase(
            response=self.response,
            project=project,
            ml_model_repo=ml_model_repo,
            ml_model_name=model_name,
            images_list=images_list,
            service=self._backend_client,
            folder=folder,
        )
        use_case.execute()
        return self._response

    def list_images(
        self, project_name: str, annotation_status: str = None, name_prefix: str = None,
    ):
        project = self._get_project(project_name)

        use_case = usecases.GetAllImagesUseCase(
            response=self.response,
            project=project,
            service_provider=self._backend_client,
            annotation_status=annotation_status,
            name_prefix=name_prefix,
        )
        use_case.execute()
        return self._response

    def upload_file_to_s3(self, to_s3_bucket, path, s3_key: str):
        use_case = usecases.UploadFileToS3UseCase(
            response=Response(), to_s3_bucket=to_s3_bucket, path=path, s3_key=s3_key
        )
        use_case.execute()

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
            response=self.response, ml_models_repo=ml_models_repo, condition=condition
        )
        use_case.execute()
        return self._response
