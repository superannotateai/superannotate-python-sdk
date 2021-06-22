import copy
import io
import uuid
from abc import ABC
from abc import abstractmethod
from pathlib import Path
from typing import Iterable
from typing import List
from typing import Optional

import src.lib.core as constances
from src.lib.core.conditions import Condition
from src.lib.core.conditions import CONDITION_EQ as EQ
from src.lib.core.entities import AnnotationClassEntity
from src.lib.core.entities import FolderEntity
from src.lib.core.entities import ImageFileEntity
from src.lib.core.entities import ImageInfoEntity
from src.lib.core.entities import ProjectEntity
from src.lib.core.entities import ProjectSettingEntity
from src.lib.core.entities import TeamEntity
from src.lib.core.entities import WorkflowEntity
from src.lib.core.exceptions import AppException
from src.lib.core.exceptions import AppValidationException
from src.lib.core.plugin import ImagePlugin
from src.lib.core.repositories import BaseManageableRepository
from src.lib.core.repositories import BaseProjectRelatedManageableRepository
from src.lib.core.repositories import BaseReadOnlyRepository
from src.lib.core.response import Response
from src.lib.core.serviceproviders import SuerannotateServiceProvider
from src.lib.core.enums import ProjectType


class BaseUseCase(ABC):
    def __init__(self, response: Response):
        self._response = response
        self._errors = []

    @abstractmethod
    def execute(self):
        raise NotImplementedError

    def _validate(self):
        for name in dir(self):
            try:
                if name.startswith("validate_"):
                    method = getattr(self, name)
                    method()
            except AppValidationException as e:
                self._errors.append(e)

    def is_valid(self):
        self._validate()
        return not self._errors


class GetProjectsUseCase(BaseUseCase):
    def __init__(
        self,
        response: Response,
        condition: Condition,
        team_id: int,
        projects: BaseManageableRepository,
    ):
        super().__init__(response)
        self._condition = condition
        self._projects = projects
        self._team_id = team_id

    def execute(self):
        if self.is_valid():
            condition = self._condition & Condition("team_id", self._team_id, EQ)
            self._response.data = self._projects.get_all(condition)
        self._response.errors = self._errors


class CreateProjectUseCase(BaseUseCase):
    def __init__(
        self,
        response: Response,
        project: ProjectEntity,
        projects: BaseManageableRepository,
        backend_service_provider: SuerannotateServiceProvider,
        settings: List[ProjectSettingEntity] = None,
        workflows: List[WorkflowEntity] = None,
        annotation_classes: List[AnnotationClassEntity] = None,
        contributors: Iterable[dict] = None,
    ):

        super().__init__(response)
        self._project = project
        self._projects = projects
        self._settings = settings
        self._workflows = workflows
        self._annotation_classes = annotation_classes
        self._contributors = contributors
        self._backend_service = backend_service_provider

    def execute(self):
        if self.is_valid():
            # todo add status in the constanses
            self._project.status = 0
            entity = self._projects.insert(self._project)
            self._response.data = entity
            if self._settings:
                settings_repo = BaseProjectRelatedManageableRepository(
                    self._backend_service, entity
                )
                for setting in self._settings:
                    settings_repo.insert(setting)
                self._response.data.settings = self._settings
            annotation_classes_mapping = {}
            if self._annotation_classes:
                annotation_repo = BaseProjectRelatedManageableRepository(
                    self._backend_service, entity
                )
                for annotation_class in self._annotation_classes:
                    annotation_classes_mapping[
                        annotation_class.uuid
                    ] = annotation_repo.insert(annotation_class)
                self._response.data.annotation_classes = self._annotation_classes
            if self._workflows:
                workflow_repo = BaseProjectRelatedManageableRepository(
                    self._backend_service, entity
                )
                for workflow in self._workflows:
                    workflow.project_id = entity.uuid
                    workflow.class_id = annotation_classes_mapping.get(
                        workflow.class_id
                    )
                    workflow_repo.insert(workflow)
                self._response.data.workflows = self._workflows

            if self._contributors:
                for contributor in self.contributors:
                    self._backend_service.share_project(
                        entity.uuid,
                        entity.team_id,
                        contributor.get("id"),
                        contributor.get("role"),
                    )
                self._response.data.contributors = self._contributors
        else:
            self._response.errors = self._errors

    def validate_project_name_uniqueness(self):
        condition = Condition("name", self._project.name, EQ) & Condition(
            "team_id", self._project.team_id, EQ
        )
        if self._projects.get_all(condition):
            raise AppValidationException(
                f"Project name {self._project.name} is not unique. "
                f"To use SDK please make project names unique."
            )


class DeleteProjectUseCase(BaseUseCase):
    def __init__(
        self,
        response: Response,
        project: ProjectEntity,
        projects: BaseManageableRepository,
    ):

        super().__init__(response)
        self._project = project
        self._projects = projects

    def execute(self):
        if self.is_valid():
            self._projects.delete(self._project.uuid)
        else:
            self._response.errors = self._errors


class UpdateProjectUseCase(BaseUseCase):
    def __init__(
        self,
        response: Response,
        project: ProjectEntity,
        projects: BaseManageableRepository,
    ):

        super().__init__(response)
        self._project = project
        self._projects = projects

    def execute(self):
        if self.is_valid():
            self._projects.update(self._project)
        else:
            self._response.errors = self._errors


class ImageUploadUseCas(BaseUseCase):
    def __init__(
        self,
        response: Response,
        project: ProjectEntity,
        project_settings: BaseReadOnlyRepository,
        backend_service_provider: SuerannotateServiceProvider,
        images: List[ImageInfoEntity],
        annotation_status: Optional[str] = None,
        image_quality: Optional[str] = None,
    ):
        super().__init__(response)
        self._project = project
        self._project_settings = project_settings
        self._backend = backend_service_provider
        self._images = images
        self._annotation_status = annotation_status
        self._image_quality = image_quality

    @property
    def image_quality(self):
        if not self._image_quality:
            for setting in self._project_settings.get_all():
                if setting.attribute == "ImageQuality":
                    if setting.value == 60:
                        return "compressed"
                    elif setting.value == 100:
                        return "original"
                    raise AppException("NA ImageQuality value")
        return self._image_quality

    @property
    def upload_state_code(self) -> int:
        return constances.UploadState.BASIC.value

    @property
    def annotation_status_code(self):
        if not self._annotation_status:
            return constances.AnnotationStatus.NOT_STARTED.value
        return constances.AnnotationStatus[self._annotation_status.upper()].value

    def execute(self):
        images = []
        meta = {}
        for image in self._images:
            images.append({"name": image.name, "path": image.path})
            meta[image.name] = {"width": image.width, "height": image.height}

        self._backend.attach_files(
            project_id=self._project.uuid,
            team_id=self._project.team_id,
            files=images,
            annotation_status_code=self.annotation_status_code,
            upload_state_code=self.upload_state_code,
            meta=meta,
        )

    def validate_upload_state(self):
        if self._project.upload_state == constances.UploadState.EXTERNAL.value:
            raise AppValidationException("Invalid upload state.")


class UploadImageS3UseCas(BaseUseCase):
    def __init__(
        self,
        response: Response,
        project: ProjectEntity,
        project_settings: BaseReadOnlyRepository,
        image_path: str,
        image: io.BytesIO,
        s3_repo: BaseManageableRepository,
        upload_path: str,
    ):
        super().__init__(response)
        self._project = project
        self._project_settings = project_settings
        self._image_path = image_path
        self._image = image
        self._s3_repo = s3_repo
        self._upload_path = upload_path

    @property
    def max_resolution(self) -> int:
        if self._project.project_type == ProjectType.VECTOR.value:
            return constances.MAX_VECTOR_RESOLUTION
        elif self._project.project_type == ProjectType.PIXEL.value:
            return constances.MAX_PIXEL_RESOLUTION

    def execute(self):
        image_name = Path(self._image_path).name

        image_processor = ImagePlugin(self._image, self.max_resolution)

        origin_width, origin_height = image_processor.get_size()
        thumb_image, _, _ = image_processor.generate_thumb()
        huge_image, huge_width, huge_height = image_processor.generate_huge()
        low_resolution_image, _, _ = image_processor.generate_low_resolution()

        image_key = (
            self._upload_path + str(uuid.uuid4()) + Path(self._image_path).suffix
        )

        file_entity = ImageFileEntity(uuid=image_key, data=self._image)

        thumb_image_name = image_key + "___thumb.jpg"
        thumb_image_entity = ImageFileEntity(uuid=thumb_image_name, data=thumb_image)
        self._s3_repo.insert(thumb_image_entity)

        low_resolution_image_name = image_key + "___lores.jpg"
        low_resolution_file_entity = ImageFileEntity(
            uuid=low_resolution_image_name, data=low_resolution_image
        )
        self._s3_repo.insert(low_resolution_file_entity)

        huge_image_name = image_key + "___huge.jpg"
        huge_file_entity = ImageFileEntity(
            uuid=huge_image_name,
            data=huge_image,
            metadata={"height": huge_width, "weight": huge_height},
        )
        self._s3_repo.insert(huge_file_entity)

        self._s3_repo.insert(file_entity)
        self._response.data = ImageInfoEntity(
            name=image_name,
            path=image_key,
            width=origin_width,
            height=origin_height,
        )


class CreateFolderUseCase(BaseUseCase):
    def __init__(
        self,
        response: Response,
        folder: FolderEntity,
        folders: BaseManageableRepository,
    ):
        super().__init__(response)
        self._folder = folder
        self._folders = folders

    def execute(self):
        self._response.data = self._folders.insert(self._folder)

    def validate_folder_name(self):
        if (
            len(
                set(self._folder.name).intersection(
                    constances.SPECIAL_CHARACTERS_IN_PROJECT_FOLDER_NAMES
                )
            )
            > 0
        ):
            raise AppValidationException("New folder name has special characters.")


class CloneProjectUseCase(BaseUseCase):
    def __init__(
        self,
        response: Response,
        project: ProjectEntity,
        project_to_create: ProjectEntity,
        projects: BaseManageableRepository,
        settings: BaseManageableRepository,
        workflows: BaseManageableRepository,
        annotation_classes: BaseManageableRepository,
        backend_service_provider: SuerannotateServiceProvider,
        include_annotation_classes: bool = True,
        include_settings: bool = True,
        include_workflow: bool = True,
        include_contributors: bool = False,
    ):
        super().__init__(response)
        self._project = project
        self._project_to_create = project_to_create
        self._projects = projects
        self._settings = settings
        self._workflows = workflows
        self._annotation_classes = annotation_classes
        self._backend_service = backend_service_provider
        self._include_annotation_classes = include_annotation_classes
        self._include_settings = include_settings
        self._include_workflow = include_workflow
        self._include_contributors = include_contributors

    def execute(self):
        project = self._projects.insert(self._project_to_create)
        self._response.data = project
        annotation_classes_mapping = {}
        if self._include_annotation_classes:
            annotation_classes = self._annotation_classes.get_all()
            for annotation_class in annotation_classes:
                annotation_class_copy = copy.copy(annotation_class)
                annotation_class_copy.project_id = project.uuid
                annotation_classes_mapping[
                    annotation_class.uuid
                ] = self._annotation_classes.insert(annotation_class_copy).uuid

        if self._include_contributors:
            for user in self._project.users:
                self._backend_service.share_project(
                    project.uuid, project.team_id, user.get("id"), user.get("role")
                )

        if self._include_settings:
            for setting in self._settings.get_all():
                setting_copy = copy.copy(setting)
                setting_copy.project_id = project.uuid
                self._settings.insert(setting)

        if self._include_workflow:
            for workflow in self._workflows.get_all():
                workflow_copy = copy.copy(workflow)
                workflow_copy.project_id = project.uuid
                workflow_copy.class_id = annotation_classes_mapping[workflow.class_id]
                self._workflows.insert(workflow_copy)


class AttachFileUrls(BaseUseCase):
    def __init__(
        self,
        response: Response,
        project: ProjectEntity,
        attachments: List[str],
        limit: int,
        backend_service_provider: SuerannotateServiceProvider,
        annotation_status: int = constances.AnnotationStatus.NOT_STARTED.value,
    ):
        super().__init__(response)
        self._attachments = attachments
        self._project = project
        self._limit = limit
        self._backend_service = backend_service_provider
        self._annotation_status_code = annotation_status

    def execute(self):
        attachments_to_upload = self._attachments[: self._limit]
        attachments_data = []
        for attachment in attachments_to_upload:
            attachments_data.append(
                {"name": Path(attachment).suffix, "path": attachment}
            )
        self._backend_service.attach_files(
            project_id=self._project.uuid,
            team_id=self._project.team_id,
            files=attachments_data,
            annotation_status_code=self._annotation_status_code,
            upload_state_code=constances.UploadState.EXTERNAL.value,
            # todo rewrite
            meta=None,
        )


class PrepareExportUseCase(BaseUseCase):
    def __init__(
        self,
        response: Response,
        project: ProjectEntity,
        folder_names: List[str],
        backend_service_provider: SuerannotateServiceProvider,
        include_fuse: bool,
        only_pinned: bool,
        annotation_statuses: List[str] = None,
    ):
        super().__init__(response),
        self._project = project
        self._folder_names = folder_names
        self._backend_service = backend_service_provider
        self._annotation_statuses = annotation_statuses
        self._include_fuse = (include_fuse,)
        self._only_pinned = only_pinned

    def execute(self):
        if self._project.upload_state == constances.UploadState.EXTERNAL.value:
            self._include_fuse = False

        if not self._annotation_statuses:
            self._annotation_statuses = (
                constances.AnnotationStatus.IN_PROGRESS.name,
                constances.AnnotationStatus.COMPLETED.name,
                constances.AnnotationStatus.QUALITY_CHECK.name,
                constances.AnnotationStatus.RETURNED.name,
            )

        res = self._backend_service.prepare_export(
            project_id=self._project.uuid,
            team_id=self._project.team_id,
            folders=self._folder_names,
            annotation_statuses=self._annotation_statuses,
            include_fuse=self._include_fuse,
            only_pinned=self._only_pinned,
        )
        self._response.data = res


class GetTeamUseCase(BaseUseCase):
    def __init__(self, response: Response, teams: BaseReadOnlyRepository, team_id: int):
        super().__init__(response)
        self._teams = teams
        self._team_id = team_id

    def execute(self):
        self._response.data = self._teams.get_one(self._team_id)


class InviteContributorUseCase(BaseUseCase):
    def __init__(
        self,
        response: Response,
        backend_service_provider: SuerannotateServiceProvider,
        email: str,
        team_id: int,
        is_admin: bool = False,
    ):
        super().__init__(response)
        self._backend_service = backend_service_provider
        self._email = email
        self._team_id = team_id
        self._is_admin = is_admin

    def execute(self):
        role = (
            constances.UserRole.ADMIN.value
            if self._is_admin
            else constances.UserRole.ANNOTATOR.value
        )
        self._backend_service.invite_contributor(
            team_id=self._team_id, email=self._email, user_role=role
        )


class DeleteContributorInvitationUseCase(BaseUseCase):
    def __init__(
        self,
        response: Response,
        backend_service_provider: SuerannotateServiceProvider,
        team: TeamEntity,
        email: str,
    ):
        super().__init__(response)
        self._backend_service = backend_service_provider
        self._email = email
        self._team = team

    def execute(self):
        for invite in self._team.pending_invitations:
            if invite["email"] == self._email:
                self._backend_service.delete_team_invitation(
                    self._team.uuid, invite["token"], self._email
                )


class SearchContributorsUseCase(BaseUseCase):
    def __init__(
        self,
        response: Response,
        backend_service_provider: SuerannotateServiceProvider,
        team_id: int,
        condition: Condition = None,
    ):
        super().__init__(response)
        self._backend_service = backend_service_provider
        self._team_id = team_id
        self._condition = condition

    def execute(self):
        res = self._backend_service.search_team_contributors(
            self._team_id, self._condition.build_query()
        )
        self._response.data = res
