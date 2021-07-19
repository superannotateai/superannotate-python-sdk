import copy
import io
from typing import Iterable
from typing import List

import lib.core as constances
from src.lib.core.conditions import Condition
from src.lib.core.conditions import CONDITION_EQ as EQ
from src.lib.core.entities import AnnotationClassEntity
from src.lib.core.entities import FolderEntity
from src.lib.core.entities import ImageEntity
from src.lib.core.entities import ProjectEntity
from src.lib.core.exceptions import AppException
from src.lib.core.response import Response
from src.lib.core.usecases import AssignFolderUseCase
from src.lib.core.usecases import AssignImagesUseCase
from src.lib.core.usecases import AttachFileUrlsUseCase
from src.lib.core.usecases import AttachImagesUseCase
from src.lib.core.usecases import CloneProjectUseCase
from src.lib.core.usecases import CopyImageAnnotationClasses
from src.lib.core.usecases import CreateAnnotationClassesUseCase
from src.lib.core.usecases import CreateAnnotationClassUseCase
from src.lib.core.usecases import CreateFolderUseCase
from src.lib.core.usecases import CreateFuseImageUseCase
from src.lib.core.usecases import CreateProjectUseCase
from src.lib.core.usecases import DeleteAnnotationClassUseCase
from src.lib.core.usecases import DeleteContributorInvitationUseCase
from src.lib.core.usecases import DeleteFolderUseCase
from src.lib.core.usecases import DeleteImagesUseCase
from src.lib.core.usecases import DeleteImageUseCase
from src.lib.core.usecases import DeleteProjectUseCase
from src.lib.core.usecases import DownloadAnnotationClassesUseCase
from src.lib.core.usecases import DownloadAzureCloudImages
from src.lib.core.usecases import DownloadGoogleCloudImages
from src.lib.core.usecases import DownloadImageAnnotationsUseCase
from src.lib.core.usecases import DownloadImageFromPublicUrlUseCase
from src.lib.core.usecases import DownloadImagePreAnnotationsUseCase
from src.lib.core.usecases import DownloadImageUseCase
from src.lib.core.usecases import ExtractFramesUseCase
from src.lib.core.usecases import GetAnnotationClassesUseCase
from src.lib.core.usecases import GetAnnotationClassUseCase
from src.lib.core.usecases import GetExportsUseCase
from src.lib.core.usecases import GetFolderUseCase
from src.lib.core.usecases import GetImageAnnotationsUseCase
from src.lib.core.usecases import GetImageBytesUseCase
from src.lib.core.usecases import GetImageMetadataUseCase
from src.lib.core.usecases import GetImagePreAnnotationsUseCase
from src.lib.core.usecases import GetImagesUseCase
from src.lib.core.usecases import GetImageUseCase
from src.lib.core.usecases import GetProjectFoldersUseCase
from src.lib.core.usecases import GetProjectImageCountUseCase
from src.lib.core.usecases import GetProjectMetadataUseCase
from src.lib.core.usecases import GetProjectsUseCase
from src.lib.core.usecases import GetS3ImageUseCase
from src.lib.core.usecases import GetSettingsUseCase
from src.lib.core.usecases import GetTeamUseCase
from src.lib.core.usecases import GetWorkflowsUseCase
from src.lib.core.usecases import ImagesBulkCopyUseCase
from src.lib.core.usecases import ImagesBulkMoveUseCase
from src.lib.core.usecases import InviteContributorUseCase
from src.lib.core.usecases import PrepareExportUseCase
from src.lib.core.usecases import SearchContributorsUseCase
from src.lib.core.usecases import SearchFolderUseCase
from src.lib.core.usecases import SetImageAnnotationStatuses
from src.lib.core.usecases import SetWorkflowUseCase
from src.lib.core.usecases import ShareProjectUseCase
from src.lib.core.usecases import UnAssignFolderUseCase
from src.lib.core.usecases import UnAssignImagesUseCase
from src.lib.core.usecases import UnShareProjectUseCase
from src.lib.core.usecases import UpdateFolderUseCase
from src.lib.core.usecases import UpdateImageUseCase
from src.lib.core.usecases import UpdateProjectUseCase
from src.lib.core.usecases import UpdateSettingsUseCase
from src.lib.core.usecases import UploadAnnotationsUseCase
from src.lib.core.usecases import UploadImageS3UseCas
from src.lib.core.usecases import GetProjectByNameUseCase

from src.lib.core.usecases import UploadS3ImagesBackendUseCase
from src.lib.infrastructure.repositories import AnnotationClassRepository
from src.lib.infrastructure.repositories import ConfigRepository
from src.lib.infrastructure.repositories import FolderRepository
from src.lib.infrastructure.repositories import ImageRepository
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
        self._project = None

    @property
    def response(self):
        # return self._response
        return Response()

    @property
    def projects(self):
        return ProjectRepository(self._backend_client)

    @property
    def teams(self):
        return TeamRepository(self._backend_client)

    @property
    def images(self):
        return ImageRepository(self._backend_client)

    @property
    def configs(self):
        return ConfigRepository()

    @property
    def team_id(self) -> int:
        return int(self.configs.get_one("token").value.split("=")[-1])

    def get_auth_data(self, project_id: int, team_id: int, folder_id: int):
        return self._backend_client.get_s3_upload_auth_token(
            team_id, folder_id, project_id
        )

    def get_s3_repository(
        self, team_id: int, project_id: int, folder_id: int, bucket: str = None
    ):
        if not self._s3_upload_auth_data:
            self._s3_upload_auth_data = self.get_auth_data(
                project_id, team_id, folder_id
            )

        return S3Repository(
            self._s3_upload_auth_data["accessKeyId"],
            self._s3_upload_auth_data["secretAccessKey"],
            self._s3_upload_auth_data["sessionToken"],
            self._s3_upload_auth_data["bucket"],
        )

    @property
    def s3_repo(self):
        return S3Repository


class Controller(BaseController):
    def _get_project(self, name: str):
        if not self._project or self._project.name != name:
            response = Response()
            use_case = GetProjectByNameUseCase(
                response=response,
                name=name,
                team_id=self.team_id,
                projects=ProjectRepository(service=self._backend_client)
            )
            use_case.execute()
            self._project = response.data
        return self._project

    def _get_folder(self, project: ProjectEntity, name: str = None):
        name = self.get_folder_name(name)
        folders = FolderRepository(self._backend_client, project)
        return folders.get_one(
            Condition("name", name, EQ)
            & Condition("team_id", self.team_id, EQ)
            & Condition("project_id", project.uuid, EQ)
        )

    @staticmethod
    def get_folder_name(name: str = None):
        if not name:
            return "root"
        return name

    def search_project(self, name: str, **kwargs) -> Response:
        condition = Condition("name", name, EQ)
        for key, val in kwargs.items():
            condition = condition & Condition(key, val, EQ)
        use_case = GetProjectsUseCase(
            response=self.response,
            condition=condition,
            projects=self.projects,
            team_id=self.team_id,
        )
        use_case.execute()
        return self.response

    def create_project(
        self,
        name: str,
        description: str,
        project_type: str,
        contributors: Iterable = (),
        settings: Iterable = (),
        annotation_classes: Iterable = (),
        workflows: Iterable = (),
    ) -> Response:
        entity = ProjectEntity(
            name=name,
            description=description,
            project_type=project_type,
            team_id=self.team_id,
        )
        use_case = CreateProjectUseCase(
            response=self.response,
            project=entity,
            projects=self.projects,
            backend_service_provider=self._backend_client,
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
        return self.response

    def delete_project(self, name: str):
        entities = self.projects.get_all(
            Condition("team_id", self.team_id, EQ) & Condition("name", name, EQ)
        )
        if entities and len(entities) == 1:
            use_case = DeleteProjectUseCase(self.response, entities[0], self.projects)
            use_case.execute()
            return self.response
        if entities and len(entities) > 1:
            raise AppException("There are duplicated names.")

    def update_project(self, name: str, project_data: dict) -> Response:
        entities = self.projects.get_all(
            Condition("team_id", self.team_id, EQ) & Condition("name", name, EQ)
        )
        project = entities[0]
        if entities and len(entities) == 1:
            project.name = project_data["name"]
            use_case = UpdateProjectUseCase(self.response, project, self.projects)
            use_case.execute()
            return self.response
        raise AppException("There are duplicated names.")

    def upload_images(
        self,
        project_name: str,
        images: List[ImageEntity],
        annotation_status: str = None,
        image_quality: str = None,
    ):
        project = self._get_project(project_name)
        use_case = AttachImagesUseCase(
            response=self.response,
            project=project,
            project_settings=ProjectSettingsRepository(self._backend_client, project),
            backend_service_provider=self._backend_client,
            images=images,
            annotation_status=annotation_status,
            image_quality=image_quality,
        )
        use_case.execute()
        return self.response

    def upload_image_to_s3(
        self,
        project_name: str,
        image_path: str,  # image path to upload
        image_bytes: io.BytesIO,
        folder_name: str = None,  # project folder path
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)
        s3_repo = self.get_s3_repository(self.team_id, project.uuid, folder.uuid,)
        use_case = UploadImageS3UseCas(
            response=self.response,
            project=project,
            project_settings=ProjectSettingsRepository(self._backend_client, project),
            image_path=image_path,
            image=image_bytes,
            s3_repo=s3_repo,
            upload_path=self._s3_upload_auth_data["filePath"],
        )
        use_case.execute()
        return self.response

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
        projects = self.projects.get_all(
            Condition("name", from_name, EQ) & Condition("team_id", self.team_id, EQ)
        )
        if projects:
            project_to_create = copy.copy(projects[0])
            project_to_create.name = name
            project_to_create.description = project_description
            use_case = CloneProjectUseCase(
                self.response,
                project=projects[0],
                project_to_create=project_to_create,
                projects=self.projects,
                settings=ProjectSettingsRepository(self._backend_client, projects[0]),
                workflows=WorkflowRepository(self._backend_client, projects[0]),
                annotation_classes=AnnotationClassRepository(
                    self._backend_client, projects[0]
                ),
                backend_service_provider=self._backend_client,
                include_contributors=copy_contributors,
                include_settings=copy_settings,
                include_workflow=copy_workflow,
                include_annotation_classes=copy_annotation_classes,
            )
            use_case.execute()
        return self.response

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

        use_case = AttachFileUrlsUseCase(
            response=self.response,
            project=project,
            folder=folder,
            attachments=files,
            limit=limit,
            backend_service_provider=self._backend_client,
            annotation_status=annotation_status,
        )
        use_case.execute()
        return self.response

    def create_folder(self, project: str, folder_name: str):
        projects = ProjectRepository(service=self._backend_client).get_all(
            condition=Condition("name", project, EQ)
            & Condition("team_id", self.team_id, EQ)
        )
        project = projects[0]
        folder = FolderEntity(
            name=folder_name, project_id=project.uuid, team_id=project.team_id
        )
        use_case = CreateFolderUseCase(
            response=self.response,
            folder=folder,
            folders=FolderRepository(self._backend_client, project),
        )
        use_case.execute()
        return self.response

    def get_folder(self, project_name: str, folder_name: str):
        project = self._get_project(project_name)
        use_case = GetFolderUseCase(
            response=self.response,
            project=project,
            folders=FolderRepository(self._backend_client, project),
            folder_name=folder_name,
        )
        use_case.execute()
        return self.response

    def search_folder(self, project_name: str, **kwargs):
        condition = None
        if kwargs:
            conditions_iter = iter(kwargs)
            key = next(conditions_iter)
            condition = Condition(key, kwargs[key], EQ)
            for key, val in conditions_iter:
                condition = condition & Condition(key, val, EQ)

        project = self._get_project(project_name)
        use_case = SearchFolderUseCase(
            response=self.response,
            project=project,
            folders=FolderRepository(self._backend_client, project),
            condition=condition,
        )
        use_case.execute()
        return self.response

    def get_project_folders(
        self, project_name: str,
    ):
        project = self._get_project(project_name)
        use_case = GetProjectFoldersUseCase(
            response=self.response,
            project=project,
            folders=FolderRepository(self._backend_client, project),
        )
        use_case.execute()
        return self.response

    def delete_folders(self, project_name: str, folder_names: List[str]):
        project = self._get_project(project_name)
        folders = self.get_project_folders(project_name).data

        use_case = DeleteFolderUseCase(
            response=self.response,
            project=project,
            folders=FolderRepository(self._backend_client, project),
            folders_to_delete=[
                folder for folder in folders if folder.name in folder_names
            ],
        )
        use_case.execute()
        return self.response

    def prepare_export(
        self,
        project: ProjectEntity,
        folder_names: List[str],
        include_fuse: bool,
        only_pinned: bool,
        annotation_statuses: List[str] = None,
    ):

        use_case = PrepareExportUseCase(
            response=self.response,
            project=project,
            folder_names=folder_names,
            backend_service_provider=self._backend_client,
            include_fuse=include_fuse,
            only_pinned=only_pinned,
            annotation_statuses=annotation_statuses,
        )
        use_case.execute()

        return self.response

    def get_team(self):
        use_case = GetTeamUseCase(
            response=self.response, teams=self.teams, team_id=self.team_id
        )
        use_case.execute()
        return self.response

    def invite_contributor(self, email: str, is_admin: bool):
        use_case = InviteContributorUseCase(
            response=self.response,
            backend_service_provider=self._backend_client,
            email=email,
            team_id=self.team_id,
            is_admin=is_admin,
        )
        use_case.execute()
        return self.response

    def delete_contributor_invitation(self, email: str):
        team = self.teams.get_one(self.team_id)
        use_case = DeleteContributorInvitationUseCase(
            response=self.response,
            backend_service_provider=self._backend_client,
            email=email,
            team=team,
        )
        use_case.execute()
        return self.response

    def search_team_contributors(self, **kwargs):
        condition = None
        if kwargs:
            conditions_iter = iter(kwargs)
            key = next(conditions_iter)
            condition = Condition(key, kwargs[key], EQ)
            for key, val in conditions_iter:
                condition = condition & Condition(key, val, EQ)

        use_case = SearchContributorsUseCase(
            response=self.response,
            backend_service_provider=self._backend_client,
            team_id=self.team_id,
            condition=condition,
        )
        use_case.execute()
        return self.response

    def search_images(
        self,
        project_name: str,
        folder_path: str = None,
        annotation_status: str = None,
        image_name_prefix: str = None,
    ):
        project = self._get_project(project_name)
        if not folder_path:
            folder = self._get_folder(project, "root")
        else:
            folder = self._get_folder(project, folder_path)
        use_case = GetImagesUseCase(
            response=self.response,
            project=project,
            folder=folder,
            images=self.images,
            annotation_status=annotation_status,
            image_name_prefix=image_name_prefix,
        )
        use_case.execute()
        return self.response

    def _get_image(
        self, project: ProjectEntity, image_name: str, folder_path: str = None,
    ) -> ImageEntity:
        response = Response()
        folder = self._get_folder(project, folder_path)
        use_case = GetImageUseCase(
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
        use_case = UpdateFolderUseCase(
            response=self.response,
            folders=FolderRepository(self._backend_client, project),
            folder=folder,
        )
        use_case.execute()
        return self.response

    def get_image_bytes(
        self,
        project_name: str,
        image_name: str,
        folder_name: str = None,
        image_variant: str = None,
    ):
        project = self._get_project(project_name)
        image = self._get_image(project, image_name, folder_name)
        use_case = GetImageBytesUseCase(
            response=self.response,
            image=image,
            backend_service_provider=self._backend_client,
            image_variant=image_variant,
        )
        use_case.execute()
        return self.response

    def copy_image_annotation_classes(
        self, from_project_name: str, to_project_name: str, image_name: str
    ):
        from_project = self._get_project(from_project_name)
        image = self._get_image(from_project, image_name)
        to_project = self._get_project(to_project_name)
        uploaded_image = self._get_image(to_project, image_name)

        use_case = CopyImageAnnotationClasses(
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
        use_case = UpdateImageUseCase(
            response=self.response, image=image, images=self.images
        )
        use_case.execute()

    def download_image_from_public_url(
        self, project_name: str, image_url: str, image_name: str = None
    ):
        response = Response()
        use_case = DownloadImageFromPublicUrlUseCase(
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
        use_case = ImagesBulkCopyUseCase(
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
        return self.response

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
        use_case = ImagesBulkMoveUseCase(
            response=self.response,
            project=project,
            from_folder=from_folder,
            to_folder=to_folder,
            image_names=image_names,
            backend_service_provider=self._backend_client,
        )
        use_case.execute()
        return self.response

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
        use_case = GetProjectMetadataUseCase(
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
        return self.response

    def get_project_settings(self, project_name: str):
        project_entity = self._get_project(project_name)
        settings_use_case = GetSettingsUseCase(
            response=self.response,
            settings=ProjectSettingsRepository(
                service=self._backend_client, project=project_entity
            ),
        )
        settings_use_case.execute()
        return self.response

    def get_project_workflow(self, project_name: str):
        project_entity = self._get_project(project_name)
        workflows_use_case = GetWorkflowsUseCase(
            workflows=WorkflowRepository(
                service=self._backend_client, project=project_entity
            ),
            response=self.response,
        )
        workflows_use_case.execute()
        return self.response

    def search_annotation_classes(self, project_name: str, name_prefix: str = None):
        project_entity = self._get_project(project_name)
        annotation_classes_use_case = GetAnnotationClassesUseCase(
            response=self.response,
            classes=AnnotationClassRepository(
                service=self._backend_client, project=project_entity
            ),
            condition=Condition("name", name_prefix, EQ),
        )
        annotation_classes_use_case.execute()
        return self.response

    def set_project_settings(self, project_name: str, new_settings: List[dict]):
        project_entity = self._get_project(project_name)
        new_settings_response = Response()
        update_settings_use_case = UpdateSettingsUseCase(
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
        delete_image_user_case = DeleteImageUseCase(
            response=self.response,
            images=ImageRepository(service=self._backend_client),
            image=image,
            team_id=project_entity.team_id,
            project_id=project_entity.uuid,
        )
        delete_image_user_case.execute()
        return self._response

    def get_image_metadata(self, project_name, image_names):
        project_entity = self._get_project(project_name)

        get_image_metadata_use_case = GetImageMetadataUseCase(
            response=self.response,
            image_names=image_names,
            team_id=project_entity.team_id,
            project_id=project_entity.uuid,
            service=self._backend_client,
        )
        get_image_metadata_use_case.execute()
        return self.response

    def set_images_annotation_statuses(
        self,
        project_name: str,
        folder_name: str,
        image_names: list,
        annotation_status: str,
    ):
        project_entity = self._get_project(project_name)
        folder_entity = self._get_folder(project_entity, folder_name)
        set_images_annotation_statuses_use_case = SetImageAnnotationStatuses(
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

        use_case = DeleteImagesUseCase(
            response=self.response,
            project=project,
            folder=folder,
            images=self.images,
            image_names=image_names,
            backend_service_provider=self._backend_client,
        )
        use_case.execute()
        return self.response

    def assign_images(
        self, project_name: str, folder_name: str, image_names: list, user: str
    ):
        project_entity = self._get_project(project_name)
        assign_images_use_case = AssignImagesUseCase(
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
        use_case = UnAssignImagesUseCase(
            response=self.response,
            project_entity=project,
            service=self._backend_client,
            folder_name=folder_name,
            image_names=image_names,
        )
        use_case.execute()

    def un_assign_folder(self, project_name: str, folder_name: str):
        project_entity = self._get_project(project_name)
        use_case = UnAssignFolderUseCase(
            response=self.response,
            service=self._backend_client,
            project_entity=project_entity,
            folder_name=folder_name,
        )
        use_case.execute()

    def assign_folder(self, project_name: str, folder_name: str, users: List[str]):
        project_entity = self._get_project(project_name)
        use_case = AssignFolderUseCase(
            response=self.response,
            service=self._backend_client,
            project_entity=project_entity,
            folder_name=folder_name,
            users=users,
        )
        use_case.execute()

    def share_project(self, project_name: str, user: str, user_role: str):
        project_entity = self._get_project(project_name)
        share_project_use_case = ShareProjectUseCase(
            response=self.response,
            service=self._backend_client,
            project_entity=project_entity,
            user_id=user,
            user_role=user_role,
        )
        share_project_use_case.execute()

    def un_share_project(self, project_name: str, user: str):
        project_entity = self._get_project(project_name)
        use_case = UnShareProjectUseCase(
            response=self.response,
            service=self._backend_client,
            project_entity=project_entity,
            user_id=user,
        )
        use_case.execute()

    def download_images_from_google_clout(
        self, project_name: str, bucket_name: str, folder_name: str, download_path: str
    ):
        use_case = DownloadGoogleCloudImages(
            response=self.response,
            project_name=project_name,
            bucket_name=bucket_name,
            folder_name=folder_name,
            download_path=download_path,
        )
        use_case.execute()
        return self.response

    def download_images_from_azure_cloud(
        self, container_name: str, folder_name: str, download_path: str
    ):
        use_case = DownloadAzureCloudImages(
            response=self.response,
            container=container_name,
            folder_name=folder_name,
            download_path=download_path,
        )
        use_case.execute()
        return self.response

    def get_image_annotations(
        self, project_name: str, folder_name: str, image_name: str
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project=project, name=folder_name)

        user_case = GetImageAnnotationsUseCase(
            response=self.response,
            service=self._backend_client,
            project=project,
            folder=folder,
            image_name=image_name,
            images=ImageRepository(service=self._backend_client),
        )
        user_case.execute()
        return self.response

    def download_image_annotations(
        self, project_name: str, folder_name: str, image_name: str, destination: str
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project=project, name=folder_name)
        user_case = DownloadImageAnnotationsUseCase(
            response=self.response,
            service=self._backend_client,
            project=project,
            folder=folder,
            image_name=image_name,
            images=ImageRepository(service=self._backend_client),
            destination=destination,
        )
        user_case.execute()
        return self.response

    def download_image_pre_annotations(
        self, project_name: str, folder_name: str, image_name: str, destination: str
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project=project, name=folder_name)
        user_case = DownloadImagePreAnnotationsUseCase(
            response=self.response,
            service=self._backend_client,
            project=project,
            folder=folder,
            image_name=image_name,
            images=ImageRepository(service=self._backend_client),
            destination=destination,
        )
        user_case.execute()
        return self.response

    def get_image_from_s3(self, s3_bucket, image_path: str):
        use_case = GetS3ImageUseCase(
            response=self.response, s3_bucket=s3_bucket, image_path=image_path
        )
        use_case.execute()
        return use_case

    def get_image_pre_annotations(
        self, project_name: str, folder_name: str, image_name: str
    ):
        project = self._get_project(project_name)
        folder = self._get_folder(project=project, name=folder_name)

        user_case = GetImagePreAnnotationsUseCase(
            response=self.response,
            service=self._backend_client,
            project=project,
            folder=folder,
            image_name=image_name,
            images=ImageRepository(service=self._backend_client),
        )
        user_case.execute()
        return self.response

    def get_exports(self, project_name: str, return_metadata: bool):
        project = self._get_project(project_name)

        use_case = GetExportsUseCase(
            response=self.response,
            service=self._backend_client,
            project=project,
            return_metadata=return_metadata,
        )
        use_case.execute()

        return self.response

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
        use_case = UploadS3ImagesBackendUseCase(
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
        return self.response

    def get_project_image_count(
        self, project_name: str, folder_name: str, with_all_subfolders: bool
    ):

        project = self._get_project(project_name)
        folder = self._get_folder(project=project, name=folder_name)

        use_case = GetProjectImageCountUseCase(
            response=self.response,
            service=self._backend_client,
            project=project,
            folder=folder,
            with_all_subfolders=with_all_subfolders,
        )

        use_case.execute()
        return self.response

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
    ):
        annotation_status_code = (
            constances.AnnotationStatus.get_value(annotation_status)
            if annotation_status
            else None
        )
        project = self._get_project(project_name)
        folder = self._get_folder(project, folder_name)
        use_case = ExtractFramesUseCase(
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
        )
        use_case.execute()
        return self.response

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
        use_case = CreateAnnotationClassUseCase(
            response=self.response,
            annotation_classes=annotation_classes,
            annotation_class=annotation_class,
        )
        use_case.execute()
        return self.response

    def delete_annotation_class(self, project_name: str, annotation_class_name: str):
        project = self._get_project(project_name)
        use_case = DeleteAnnotationClassUseCase(
            response=self.response,
            annotation_class_name=annotation_class_name,
            annotation_classes_repo=AnnotationClassRepository(
                service=self._backend_client, project=project,
            ),
        )
        use_case.execute()

    def get_annotation_class(self, project_name: str, annotation_class_name: str):
        project = self._get_project(project_name)
        use_case = GetAnnotationClassUseCase(
            response=self.response,
            annotation_class_name=annotation_class_name,
            annotation_classes_repo=AnnotationClassRepository(
                service=self._backend_client, project=project,
            ),
        )
        use_case.execute()
        return self.response

    def download_annotation_classes(self, project_name: str, download_path: str):
        project = self._get_project(project_name)
        use_case = DownloadAnnotationClassesUseCase(
            response=self.response,
            annotation_classes_repo=AnnotationClassRepository(
                service=self._backend_client, project=project,
            ),
            download_path=download_path,
        )
        use_case.execute()
        return self.response

    def create_annotation_classes(self, project_name: str, annotation_classes: list):
        project = self._get_project(project_name)

        use_case = CreateAnnotationClassesUseCase(
            response=self.response,
            service=self._backend_client,
            annotation_classes_repo=AnnotationClassRepository(
                service=self._backend_client, project=project,
            ),
            annotation_classes=annotation_classes,
            project=project,
        )
        use_case.execute()
        return self.response

    def create_fuse_image(
        self,
        project_type: str,
        image_path: str,
        in_memory: bool,
        generate_overlay: bool,
    ):

        use_case = CreateFuseImageUseCase(
            response=self.response,
            project_type=project_type,
            image_path=image_path,
            in_memory=in_memory,
            generate_overlay=generate_overlay,
        )
        use_case.execute()
        return self.response

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

        use_case = DownloadImageUseCase(
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
        return self.response

    def set_project_workflow(self, project_name: str, steps: list):
        project = self._get_project(project_name)
        use_case = SetWorkflowUseCase(
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
        use_case = UploadAnnotationsUseCase(
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
        return self.response
