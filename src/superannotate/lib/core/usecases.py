import concurrent.futures
import copy
import io
import json
import logging
import os.path
import random
import time
import uuid
import zipfile
from abc import ABC
from abc import abstractmethod
from collections import defaultdict
from collections import namedtuple
from pathlib import Path
from typing import Iterable
from typing import List
from typing import Optional

import boto3
import cv2
import lib.core as constances
import numpy as np
import pandas as pd
import requests
from boto3.exceptions import Boto3Error
from lib.app.analytics.common import aggregate_annotations_as_df
from lib.app.analytics.common import consensus_plot
from lib.app.analytics.common import image_consensus
from lib.core.conditions import Condition
from lib.core.conditions import CONDITION_EQ as EQ
from lib.core.entities import AnnotationClassEntity
from lib.core.entities import FolderEntity
from lib.core.entities import ImageEntity
from lib.core.entities import ImageInfoEntity
from lib.core.entities import MLModelEntity
from lib.core.entities import ProjectEntity
from lib.core.entities import ProjectSettingEntity
from lib.core.entities import S3FileEntity
from lib.core.entities import TeamEntity
from lib.core.entities import WorkflowEntity
from lib.core.enums import ExportStatus
from lib.core.enums import ImageQuality
from lib.core.enums import ProjectType
from lib.core.exceptions import AppException
from lib.core.exceptions import AppValidationException
from lib.core.exceptions import ImageProcessingException
from lib.core.plugin import ImagePlugin
from lib.core.plugin import VideoPlugin
from lib.core.repositories import BaseManageableRepository
from lib.core.repositories import BaseReadOnlyRepository
from lib.core.response import Response
from lib.core.serviceproviders import SuerannotateServiceProvider
from PIL import UnidentifiedImageError

logger = logging.getLogger("root")


class BaseUseCase(ABC):
    def __init__(self):
        self._response = Response()

    @abstractmethod
    def execute(self) -> Response:
        raise NotImplementedError

    def _validate(self):
        for name in dir(self):
            try:
                if name.startswith("validate_"):
                    method = getattr(self, name)
                    method()
            except AppValidationException as e:
                self._response.errors = e

    def is_valid(self):
        self._validate()
        return not self._response.errors


class BaseInteractiveUseCase(BaseUseCase):
    @property
    def response(self):
        return self._response

    @property
    def data(self):
        return self.response.data

    @abstractmethod
    def execute(self):
        raise NotImplementedError


class GetProjectsUseCase(BaseUseCase):
    def __init__(
        self, condition: Condition, team_id: int, projects: BaseManageableRepository,
    ):
        super().__init__()
        self._condition = condition
        self._projects = projects
        self._team_id = team_id

    def execute(self):
        if self.is_valid():
            condition = self._condition & Condition("team_id", self._team_id, EQ)
            self._response.data = self._projects.get_all(condition)
        return self._response


class GetProjectByNameUseCase(BaseUseCase):
    def __init__(
        self, name: str, team_id: int, projects: BaseManageableRepository,
    ):
        super().__init__()
        self._name = name
        self._projects = projects
        self._team_id = team_id

    def execute(self):
        if self.is_valid():
            condition = Condition("name", self._name, EQ) & Condition(
                "team_id", self._team_id, EQ
            )
            projects = self._projects.get_all(condition)
            if not projects:
                self._response.errors = AppException("Project not found.")
            else:
                project = next(
                    (project for project in projects if project.name == self._name),
                    None,
                )
                if not project:
                    self._response.errors = AppException("Project not found")
                self._response.data = project
        return self._response


class CreateProjectUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        projects: BaseManageableRepository,
        backend_service_provider: SuerannotateServiceProvider,
        settings_repo: BaseManageableRepository,
        annotation_classes_repo: BaseManageableRepository,
        workflows_repo: BaseManageableRepository,
        settings: List[ProjectSettingEntity] = None,
        workflows: List[WorkflowEntity] = None,
        annotation_classes: List[AnnotationClassEntity] = None,
        contributors: Iterable[dict] = None,
    ):

        super().__init__()
        self._project = project
        self._projects = projects
        self._settings = settings
        self._settings_repo = settings_repo
        self._annotation_classes_repo = annotation_classes_repo
        self._workflows_repo = workflows_repo
        self._workflows = workflows
        self._annotation_classes = annotation_classes
        self._contributors = contributors
        self._backend_service = backend_service_provider

    def validate_project_name(self):
        if not self._project.name:
            raise AppValidationException("Please provide a project name.")
        condition = Condition("name", self._project.name, EQ) & Condition(
            "team_id", self._project.team_id, EQ
        )
        if self._projects.get_all(condition):
            raise AppValidationException(
                f"Project name {self._project.name} is not unique. "
                f"To use SDK please make project names unique."
            )

    def validate_description(self):
        if not self._project.description:
            raise AppValidationException("Please provide a project description.")

    def execute(self):
        if self.is_valid():
            # TODO add status in the constants

            if (
                len(
                    set(self._project.name).intersection(
                        constances.SPECIAL_CHARACTERS_IN_PROJECT_FOLDER_NAMES
                    )
                )
                > 0
            ):
                self._project.name = "".join(
                    "_"
                    if char in constances.SPECIAL_CHARACTERS_IN_PROJECT_FOLDER_NAMES
                    else char
                    for char in self._project.name
                )
                logger.warning(
                    "New project name has special characters. Special characters will be replaced by underscores."
                )

            self._project.status = 0
            entity = self._projects.insert(self._project)
            self._response.data = entity
            data = {}
            if self._settings:
                settings_repo = self._settings_repo(self._backend_service, entity)
                for setting in self._settings:
                    for new_setting in settings_repo.get_all():
                        if new_setting.attribute == setting.attribute:
                            setting_copy = copy.copy(setting)
                            setting_copy.uuid = new_setting.uuid
                            setting_copy.project_id = entity.uuid
                            settings_repo.update(setting_copy)
                data["settings"] = self._settings
            annotation_classes_mapping = {}
            if self._annotation_classes:
                annotation_repo = self._annotation_classes_repo(
                    self._backend_service, entity
                )
                for annotation_class in self._annotation_classes:
                    annotation_classes_mapping[
                        annotation_class.uuid
                    ] = annotation_repo.insert(annotation_class)
                self._response.data.annotation_classes = self._annotation_classes
            if self._workflows:
                workflow_repo = self._workflows_repo(self._backend_service, entity)
                for workflow in self._workflows:
                    workflow.project_id = entity.uuid
                    workflow.class_id = annotation_classes_mapping.get(
                        workflow.class_id
                    )
                    workflow_repo.insert(workflow)
                data["workflows"] = self._workflows

            if self._contributors:
                for contributor in self._contributors:
                    self._backend_service.share_project(
                        entity.uuid,
                        entity.team_id,
                        contributor["user_id"],
                        constances.UserRole.get_value(contributor["user_role"]),
                    )
                data["contributors"] = self._contributors

            logger.info(
                "Created project %s (ID %s) with type %s",
                self._response.data.name,
                self._response.data.uuid,
                constances.ProjectType.get_name(self._response.data.project_type),
            )
        return self._response


class DeleteProjectUseCase(BaseUseCase):
    def __init__(
        self, project_name: str, team_id: int, projects: BaseManageableRepository,
    ):

        super().__init__()
        self._project_name = project_name
        self._team_id = team_id
        self._projects = projects

    def execute(self):
        use_case = GetProjectByNameUseCase(
            name=self._project_name, team_id=self._team_id, projects=self._projects,
        )
        project_response = use_case.execute()
        if project_response.data:
            is_deleted = self._projects.delete(project_response.data)
            if is_deleted:
                logger.info("Successfully deleted project ")
            else:
                raise AppException("Couldn't delete project")


class UpdateProjectUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        project_data: dict,
        projects: BaseManageableRepository,
    ):

        super().__init__()
        self._project = project
        self._project_data = project_data
        self._projects = projects

    def validate_project_name(self):
        if self._project_data.get("name"):
            if (
                len(
                    set(self._project_data["name"]).intersection(
                        constances.SPECIAL_CHARACTERS_IN_PROJECT_FOLDER_NAMES
                    )
                )
                > 0
            ):
                self._project_data["name"] = "".join(
                    "_"
                    if char in constances.SPECIAL_CHARACTERS_IN_PROJECT_FOLDER_NAMES
                    else char
                    for char in self._project_data["name"]
                )
                logger.warning(
                    "New folder name has special characters. Special characters will be replaced by underscores."
                )
            condition = Condition("name", self._project_data["name"], EQ) & Condition(
                "team_id", self._project.team_id, EQ
            )
            if self._projects.get_all(condition):
                logger.error("There are duplicated names.")
                raise AppValidationException(
                    f"Project name {self._project.name} is not unique. "
                    f"To use SDK please make project names unique."
                )

    def execute(self):
        if self.is_valid():
            for field, value in self._project_data.items():
                setattr(self._project, field, value)
            self._projects.update(self._project)


class CloneProjectUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        project_to_create: ProjectEntity,
        projects: BaseManageableRepository,
        settings_repo,
        workflows_repo,
        annotation_classes_repo,
        backend_service_provider: SuerannotateServiceProvider,
        include_annotation_classes: bool = True,
        include_settings: bool = True,
        include_workflow: bool = True,
        include_contributors: bool = False,
    ):
        super().__init__()
        self._project = project
        self._project_to_create = project_to_create
        self._projects = projects
        self._settings_repo = settings_repo
        self._workflows_repo = workflows_repo
        self._annotation_classes_repo = annotation_classes_repo
        self._backend_service = backend_service_provider
        self._include_annotation_classes = include_annotation_classes
        self._include_settings = include_settings
        self._include_workflow = include_workflow
        self._include_contributors = include_contributors

    @property
    def annotation_classes(self):
        return self._annotation_classes_repo(self._backend_service, self._project)

    @property
    def settings(self):
        return self._settings_repo(self._backend_service, self._project)

    @property
    def workflows(self):
        return self._workflows_repo(self._backend_service, self._project)

    def validate_project_type(self):
        if self._project.project_type == constances.ProjectType.VIDEO.value:
            raise AppValidationException(
                "The function does not support projects containing videos attached with URLs"
            )

    def execute(self):
        if self.is_valid():
            project = self._projects.insert(self._project_to_create)

            annotation_classes_mapping = {}
            new_project_annotation_classes = self._annotation_classes_repo(
                self._backend_service, project
            )
            if self._include_annotation_classes:
                annotation_classes = self.annotation_classes.get_all()
                for annotation_class in annotation_classes:
                    annotation_class_copy = copy.copy(annotation_class)
                    annotation_classes_mapping[
                        annotation_class.uuid
                    ] = new_project_annotation_classes.insert(annotation_class_copy)

            if self._include_contributors:
                self._project = self._projects.get_one(
                    uuid=self._project.uuid, team_id=self._project.team_id
                )
                for user in self._project.users:
                    self._backend_service.share_project(
                        project.uuid,
                        project.team_id,
                        user.get("user_id"),
                        user.get("user_role"),
                    )

            if self._include_settings:
                new_settings = self._settings_repo(self._backend_service, project)
                for setting in self.settings.get_all():
                    for new_setting in new_settings.get_all():
                        if new_setting.attribute == setting.attribute:
                            setting_copy = copy.copy(setting)
                            setting_copy.uuid = new_setting.uuid
                            setting_copy.project_id = project.uuid
                            new_settings.update(setting_copy)

            if self._include_workflow:
                new_workflows = self._workflows_repo(self._backend_service, project)
                workflow_attributes = []
                for workflow in self.workflows.get_all():
                    workflow_data = copy.copy(workflow)
                    workflow_data.project_id = project.uuid
                    workflow_data.class_id = annotation_classes_mapping[
                        workflow.class_id
                    ].uuid
                    new_workflow = new_workflows.insert(workflow_data)
                    for attribute in workflow_data.attribute:
                        for annotation_attribute in annotation_classes_mapping[
                            workflow.class_id
                        ].attribute_groups:
                            if (
                                attribute["attribute"]["attribute_group"]["name"]
                                == annotation_attribute["name"]
                            ):
                                for annotation_attribute_value in annotation_attribute[
                                    "attributes"
                                ]:
                                    if (
                                        annotation_attribute_value["name"]
                                        == attribute["attribute"]["name"]
                                    ):
                                        workflow_attributes.append(
                                            {
                                                "workflow_id": new_workflow.uuid,
                                                "attribute_id": annotation_attribute_value[
                                                    "id"
                                                ],
                                            }
                                        )
                                        break

                    if workflow_attributes:
                        self._backend_service.set_project_workflow_attributes_bulk(
                            project_id=project.uuid,
                            team_id=project.team_id,
                            attributes=workflow_attributes,
                        )

            self._response.data = self._projects.get_one(
                uuid=project.uuid, team_id=project.team_id
            )
        return self._response


class GetImagesUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        images: BaseReadOnlyRepository,
        annotation_status: str = None,
        image_name_prefix: str = None,
    ):
        super().__init__()
        self._project = project
        self._folder = folder
        self._images = images
        self._annotation_status = annotation_status
        self._image_name_prefix = image_name_prefix

    # def validate_project_type(self):
    #     if self._project.project_type == constances.ProjectType.VIDEO.value:
    #         raise AppValidationException(
    #             "The function does not support projects containing videos attached with URLs"
    #         )

    def validate_annotation_status(self):
        if (
            self._annotation_status
            and self._annotation_status.lower()
            not in constances.AnnotationStatus.values()
        ):
            raise AppValidationException("Invalid annotations status.")

    def execute(self):
        if self.is_valid():
            condition = (
                Condition("team_id", self._project.team_id, EQ)
                & Condition("project_id", self._project.uuid, EQ)
                & Condition("folder_id", self._folder.uuid, EQ)
            )
            if self._image_name_prefix:
                condition = condition & Condition("name", self._image_name_prefix, EQ)
            if self._annotation_status:
                condition = condition & Condition(
                    "annotation_status",
                    constances.AnnotationStatus.get_value(self._annotation_status),
                    EQ,
                )

            self._response.data = self._images.get_all(condition)
        return self._response


class GetImageUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        image_name: str,
        images: BaseReadOnlyRepository,
        service: SuerannotateServiceProvider,
    ):
        super().__init__()
        self._project = project
        self._folder = folder
        self._images = images
        self._image_name = image_name
        self._service = service

    def execute(self):
        images = (
            GetBulkImages(
                service=self._service,
                project_id=self._project.uuid,
                team_id=self._project.team_id,
                folder_id=self._folder.uuid,
                images=[self._image_name],
            )
            .execute()
            .data
        )
        if images:
            self._response.data = images[0]
        else:
            raise AppException("Image not found.")
        return self._response


class UploadImageS3UseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        project_settings: List[ProjectSettingEntity],
        image_path: str,
        image: io.BytesIO,
        s3_repo: BaseManageableRepository,
        upload_path: str,
        image_quality_in_editor: str,
    ):
        super().__init__()
        self._project = project
        self._project_settings = project_settings
        self._image_path = image_path
        self._image = image
        self._s3_repo = s3_repo
        self._upload_path = upload_path
        self._image_quality_in_editor = image_quality_in_editor

    @property
    def max_resolution(self) -> int:
        if self._project.project_type == ProjectType.PIXEL.value:
            return constances.MAX_PIXEL_RESOLUTION
        return constances.MAX_VECTOR_RESOLUTION

    def execute(self):
        image_name = Path(self._image_path).name
        try:
            image_processor = ImagePlugin(self._image, self.max_resolution)
            origin_width, origin_height = image_processor.get_size()
            thumb_image, _, _ = image_processor.generate_thumb()
            huge_image, huge_width, huge_height = image_processor.generate_huge()
            quality = 60
            if not self._image_quality_in_editor:
                for setting in self._project_settings:
                    if setting.attribute == "ImageQuality":
                        quality = setting.value
            else:
                quality = ImageQuality.get_value(self._image_quality_in_editor)
            if Path(image_name).suffix[1:].upper() in ("JPEG", "JPG"):
                if quality == 100:
                    self._image.seek(0)
                    low_resolution_image = self._image
                else:
                    (
                        low_resolution_image,
                        _,
                        _,
                    ) = image_processor.generate_low_resolution(quality=quality)
            else:
                if quality == 100:
                    (
                        low_resolution_image,
                        _,
                        _,
                    ) = image_processor.generate_low_resolution(
                        quality=quality, subsampling=0
                    )
                else:
                    (
                        low_resolution_image,
                        _,
                        _,
                    ) = image_processor.generate_low_resolution(
                        quality=quality, subsampling=-1
                    )
            image_key = (
                self._upload_path + str(uuid.uuid4()) + Path(self._image_path).suffix
            )

            file_entity = S3FileEntity(uuid=image_key, data=self._image)

            thumb_image_name = image_key + "___thumb.jpg"
            thumb_image_entity = S3FileEntity(uuid=thumb_image_name, data=thumb_image)
            self._s3_repo.insert(thumb_image_entity)

            low_resolution_image_name = image_key + "___lores.jpg"
            low_resolution_file_entity = S3FileEntity(
                uuid=low_resolution_image_name, data=low_resolution_image
            )
            self._s3_repo.insert(low_resolution_file_entity)

            huge_image_name = image_key + "___huge.jpg"
            huge_file_entity = S3FileEntity(
                uuid=huge_image_name,
                data=huge_image,
                metadata={"height": huge_width, "weight": huge_height},
            )
            self._s3_repo.insert(huge_file_entity)
            file_entity.data.seek(0)
            self._s3_repo.insert(file_entity)
            self._response.data = ImageEntity(
                name=image_name,
                path=image_key,
                meta=ImageInfoEntity(width=origin_width, height=origin_height),
            )
        except (ImageProcessingException, UnidentifiedImageError) as e:
            self._response.errors = e
        return self._response


class CreateFolderUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        folders: BaseManageableRepository,
    ):
        super().__init__()
        self._project = project
        self._folder = folder
        self._folders = folders

    def validate_folder(self):
        if not self._folder.name:
            raise AppValidationException("Folder name cannot be empty.")

    def execute(self):
        if self.is_valid():
            if (
                len(
                    set(self._folder.name).intersection(
                        constances.SPECIAL_CHARACTERS_IN_PROJECT_FOLDER_NAMES
                    )
                )
                > 0
            ):
                self._folder.name = "".join(
                    "_"
                    if char in constances.SPECIAL_CHARACTERS_IN_PROJECT_FOLDER_NAMES
                    else char
                    for char in self._folder.name
                )
                logger.warning(
                    "New folder name has special characters. Special characters will be replaced by underscores."
                )
            self._folder.project_id = self._project.uuid
            self._response.data = self._folders.insert(self._folder)
        return self._response


class AttachFileUrlsUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        limit: int,
        attachments: List[ImageEntity],
        backend_service_provider: SuerannotateServiceProvider,
        annotation_status: str = None,
    ):
        super().__init__()
        self._attachments = attachments
        self._project = project
        self._limit = limit
        self._folder = folder
        self._backend_service = backend_service_provider
        self._annotation_status = annotation_status

    @property
    def annotation_status_code(self):
        if self._annotation_status:
            return constances.AnnotationStatus.get_value(self._annotation_status)
        return constances.AnnotationStatus.NOT_STARTED.value

    @property
    def upload_state_code(self) -> int:
        if self._project.project_type == constances.ProjectType.VIDEO.value:
            return constances.UploadState.EXTERNAL.value
        return constances.UploadState.BASIC.value

    def execute(self):
        response = self._backend_service.get_bulk_images(
            project_id=self._project.uuid,
            team_id=self._project.team_id,
            folder_id=self._folder.uuid,
            images=[image.name for image in self._attachments],
        )
        if isinstance(response, dict) and "error" in response:
            raise AppException(response["error"])
        duplications = [image["name"] for image in response]
        meta = {}
        to_upload = []
        for image in self._attachments:
            if not image.name:
                image.name = str(uuid.uuid4())
            if image.name not in duplications:
                to_upload.append({"name": image.name, "path": image.path})
                meta[image.name] = {
                    "width": image.meta.width,
                    "height": image.meta.height,
                }

        backend_response = self._backend_service.attach_files(
            project_id=self._project.uuid,
            folder_id=self._folder.uuid,
            team_id=self._project.team_id,
            files=to_upload[: self._limit],
            annotation_status_code=self.annotation_status_code,
            upload_state_code=self.upload_state_code,
            meta=meta,
        )
        if isinstance(backend_response, dict) and "error" in backend_response:
            self._response.errors = AppException(backend_response["error"])
        else:
            self._response.data = backend_response, duplications
        return self._response


class PrepareExportUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        folder_names: List[str],
        backend_service_provider: SuerannotateServiceProvider,
        include_fuse: bool,
        only_pinned: bool,
        annotation_statuses: List[str] = None,
    ):
        super().__init__(),
        self._project = project
        self._folder_names = folder_names
        self._backend_service = backend_service_provider
        self._annotation_statuses = annotation_statuses
        self._include_fuse = include_fuse
        self._only_pinned = only_pinned

    def validate_project_type(self):
        if self._project.project_type == constances.ProjectType.VIDEO.value:
            raise AppValidationException(
                "The function does not support projects containing videos attached with URLs"
            )

    def validate_fuse(self):
        if (
            self._project.upload_state == constances.UploadState.EXTERNAL.value
            and self._include_fuse
        ):
            raise AppValidationException(
                "Include fuse functionality is not supported for  projects containing  items attached with URLs"
            )

    def execute(self):
        if self.is_valid():
            if self._project.upload_state == constances.UploadState.EXTERNAL.value:
                self._include_fuse = False

            if not self._annotation_statuses:
                self._annotation_statuses = (
                    constances.AnnotationStatus.IN_PROGRESS.name,
                    constances.AnnotationStatus.COMPLETED.name,
                    constances.AnnotationStatus.QUALITY_CHECK.name,
                    constances.AnnotationStatus.RETURNED.name,
                    constances.AnnotationStatus.NOT_STARTED.name,
                    constances.AnnotationStatus.SKIPPED.name,
                )

            res = self._backend_service.prepare_export(
                project_id=self._project.uuid,
                team_id=self._project.team_id,
                folders=self._folder_names,
                annotation_statuses=self._annotation_statuses,
                include_fuse=self._include_fuse,
                only_pinned=self._only_pinned,
            )
            folder_str = (
                "" if self._folder_names is None else ("/" + str(self._folder_names))
            )
            logger.info(
                "Prepared export %s for project %s%s (project ID %s).",
                res["name"],
                self._project.name,
                folder_str,
                self._project.uuid,
            )
            self._response.data = res

        return self._response


class GetTeamUseCase(BaseUseCase):
    def __init__(self, teams: BaseReadOnlyRepository, team_id: int):
        super().__init__()
        self._teams = teams
        self._team_id = team_id

    def execute(self):
        try:
            self._response.data = self._teams.get_one(self._team_id)
        except Exception:
            raise AppException("Can't get team data.")
        return self._response


class InviteContributorUseCase(BaseUseCase):
    def __init__(
        self,
        backend_service_provider: SuerannotateServiceProvider,
        email: str,
        team_id: int,
        is_admin: bool = False,
    ):
        super().__init__()
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
        backend_service_provider: SuerannotateServiceProvider,
        team: TeamEntity,
        email: str,
    ):
        super().__init__()
        self._backend_service = backend_service_provider
        self._email = email
        self._team = team

    def execute(self):
        for invite in self._team.pending_invitations:
            if invite["email"] == self._email:
                self._backend_service.delete_team_invitation(
                    self._team.uuid, invite["token"], self._email
                )
        return self._response


class SearchContributorsUseCase(BaseUseCase):
    def __init__(
        self,
        backend_service_provider: SuerannotateServiceProvider,
        team_id: int,
        condition: Condition = None,
    ):
        super().__init__()
        self._backend_service = backend_service_provider
        self._team_id = team_id
        self._condition = condition

    @property
    def condition(self):
        if self._condition:
            return self._condition.build_query()

    def execute(self):
        res = self._backend_service.search_team_contributors(
            self._team_id, self.condition
        )
        self._response.data = res
        return self._response


class GetFolderUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        folders: BaseReadOnlyRepository,
        folder_name: str,
        team_id: int,
    ):
        super().__init__()
        self._project = project
        self._folders = folders
        self._folder_name = folder_name
        self._team_id = team_id

    def execute(self):
        condition = (
            Condition("name", self._folder_name, EQ)
            & Condition("team_id", self._team_id, EQ)
            & Condition("project_id", self._project.uuid, EQ)
        )
        try:
            self._response.data = self._folders.get_one(condition)
        except AppException as e:
            self._response.errors = e
        return self._response


class SearchFoldersUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        folders: BaseReadOnlyRepository,
        condition: Condition,
        folder_name: str = None,
        include_users=False,
    ):
        super().__init__()
        self._project = project
        self._folders = folders
        self._folder_name = folder_name
        self._condition = condition
        self._include_users = include_users

    def execute(self):
        condition = (
            self._condition
            & Condition("project_id", self._project.uuid, EQ)
            & Condition("team_id", self._project.team_id, EQ)
            & Condition("includeUsers", self._include_users, EQ)
        )
        if self._folder_name:
            condition &= Condition("name", self._folder_name, EQ)
        self._response.data = self._folders.get_all(condition)
        return self._response


class DeleteFolderUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        folders: BaseManageableRepository,
        folders_to_delete: List[FolderEntity],
    ):
        super().__init__()
        self._project = project
        self._folders = folders
        self._folders_to_delete = folders_to_delete

    def execute(self):
        if self._folders_to_delete:
            is_deleted = self._folders.bulk_delete(self._folders_to_delete)
            if not is_deleted:
                self._response.errors = AppException("Couldn't delete folders.")
        else:
            self._response.errors = AppException("There is no folder to delete.")
        return self._response


class UpdateFolderUseCase(BaseUseCase):
    def __init__(
        self, folders: BaseManageableRepository, folder: FolderEntity,
    ):
        super().__init__()
        self._folders = folders
        self._folder = folder

    def execute(self):
        is_updated = self._folders.update(self._folder)
        if not is_updated:
            self._response.errors = AppException("Couldn't rename folder.")
        self._response.data = self._folder
        return self._response


class GetImageBytesUseCase(BaseUseCase):
    def __init__(
        self,
        image: ImageEntity,
        backend_service_provider: SuerannotateServiceProvider,
        image_variant: str = "original",
    ):
        super().__init__()
        self._image = image
        self._backend_service = backend_service_provider
        self._image_variant = image_variant

    def execute(self):
        auth_data = self._backend_service.get_download_token(
            project_id=self._image.project_id,
            team_id=self._image.team_id,
            folder_id=self._image.folder_id,
            image_id=self._image.uuid,
            include_original=1,
        )
        download_url = auth_data[self._image_variant]["url"]
        headers = auth_data[self._image_variant]["headers"]
        response = requests.get(url=download_url, headers=headers)
        self._response.data = io.BytesIO(response.content)
        return self._response


class CopyImageAnnotationClasses(BaseUseCase):
    def __init__(
        self,
        from_project: ProjectEntity,
        to_project: ProjectEntity,
        from_image: ImageEntity,
        to_image: ImageEntity,
        from_project_s3_repo: BaseManageableRepository,
        to_project_s3_repo: BaseManageableRepository,
        to_project_annotation_classes: BaseReadOnlyRepository,
        from_project_annotation_classes: BaseReadOnlyRepository,
        backend_service_provider: SuerannotateServiceProvider,
        from_folder: FolderEntity = None,
        to_folder: FolderEntity = None,
        annotation_type: str = "MAIN",
    ):
        super().__init__()
        self._from_project = from_project
        self._to_project = to_project
        self._from_folder = from_folder
        self._to_folder = to_folder
        self._from_project_annotation_classes = from_project_annotation_classes
        self._to_project_annotation_classes = to_project_annotation_classes
        self._from_project_s3_repo = from_project_s3_repo
        self.to_project_s3_repo = to_project_s3_repo
        self._from_image = from_image
        self._to_image = to_image
        self._backend_service = backend_service_provider
        self._annotation_type = annotation_type

    @property
    def default_annotation(self):
        return {
            "annotation_json": None,
            "annotation_json_filename": None,
            "annotation_mask": None,
            "annotation_mask_filename": None,
        }

    @property
    def annotation_json_name(self):
        if self._project.project_type == constances.ProjectType.VECTOR.value:
            return f"{self._image.name}___objects.json"
        elif self._project.project_type == constances.ProjectType.PIXEL.value:
            return f"{self._image.name}___pixel.json"

    @property
    def download_auth_data(self):
        return self._backend_service.get_download_token(
            project_id=self._from_image.project_id,
            team_id=self._from_image.team_id,
            folder_id=self._from_image.folder_id,
            image_id=self._from_image.uuid,
            include_original=1,
        )

    @property
    def upload_auth_data(self):
        return self._backend_service.get_upload_token(
            project_id=self._to_image.project_id,
            team_id=self._to_image.team_id,
            folder_id=self._to_image.folder_id,
            image_id=self._to_image.uuid,
        )

    def validate_project_type(self):
        if self._from_project.project_type != self._to_project.project_type:
            raise AppValidationException("Projects are different.")

    def execute(self):
        if self._annotation_type not in self.download_auth_data["annotations"]:
            self._response.data = self.default_annotation
            return
        annotations = self.download_auth_data["annotations"][self._annotation_type][0]
        response = requests.get(
            url=annotations["annotation_json_path"]["url"],
            headers=annotations["annotation_json_path"]["headers"],
        )
        if not response.ok:
            raise AppException("Couldn't load annotations.")

        image_annotations = response.json()
        from_project_annotation_classes = (
            self._from_project_annotation_classes.get_all()
        )
        to_project_annotation_classes = self._to_project_annotation_classes.get_all()

        annotations_classes_from_copy = {
            from_annotation.uuid: from_annotation
            for from_annotation in from_project_annotation_classes
            for to_annotation in to_project_annotation_classes
            if from_annotation.name == to_annotation.name
        }

        annotations_classes_to_copy = {
            to_annotation.name: to_annotation
            for to_annotation in to_project_annotation_classes
            for from_annotation in from_project_annotation_classes
            if from_annotation.name == to_annotation.name
        }

        for instance in image_annotations["instances"]:
            if instance["classId"] < 0 or not annotations_classes_from_copy.get(
                instance["classId"]
            ):
                continue
            project_annotation_class = annotations_classes_from_copy[
                instance["classId"]
            ]
            instance["className"] = project_annotation_class.name
            if instance.get("attributes"):
                for attribute in instance["attributes"]:
                    attribute_group = None
                    if attribute.get("groupId"):
                        for group in project_annotation_class.attribute_groups:
                            if group["id"] == attribute["groupId"]:
                                attribute["groupName"] = group["name"]
                                attribute_group = group
                        if attribute.get("id") and attribute_group:
                            for attr in attribute_group["attributes"]:
                                if attr["id"] == attribute["id"]:
                                    attribute["name"] = attr["name"]

        for instance in image_annotations["instances"]:
            if (
                "className" not in instance
                and instance["className"] not in annotations_classes_to_copy
            ):
                continue
            annotation_class = annotations_classes_to_copy.get(instance["className"])
            if not annotation_class:
                instance["classId"] = -1
                continue
            attribute_groups_map = {
                group["name"]: group for group in annotation_class.attribute_groups
            }
            instance["classId"] = annotation_class.uuid
            for attribute in instance["attributes"]:
                if attribute_groups_map.get(attribute["groupName"]):
                    attribute["groupId"] = attribute_groups_map[attribute["groupName"]][
                        "id"
                    ]
                    attr_map = {
                        attr["name"]: attr
                        for attr in attribute_groups_map[attribute["groupName"]][
                            "attributes"
                        ]
                    }
                    if attribute["name"] not in attr_map:
                        del attribute["groupId"]
                        continue
                    attribute["id"] = attr_map[attribute["name"]]["id"]

        auth_data = self.upload_auth_data
        file = S3FileEntity(
            uuid=auth_data["annotation_json_path"]["filePath"],
            data=json.dumps(image_annotations),
        )
        self.to_project_s3_repo.insert(file)

        if (
            self._to_project.project_type == constances.ProjectType.PIXEL.value
            and annotations.get("annotation_bluemap_path")
            and annotations["annotation_bluemap_path"]["exist"]
        ):
            response = requests.get(
                url=annotations["annotation_bluemap_path"]["url"],
                headers=annotations["annotation_bluemap_path"]["headers"],
            )
            if not response.ok:
                raise AppException("Couldn't load annotations.")
            self.to_project_s3_repo.insert(
                S3FileEntity(
                    auth_data["annotation_bluemap_path"]["filePath"], response.content
                )
            )
        return self._response


class UpdateImageUseCase(BaseUseCase):
    def __init__(self, image: ImageEntity, images: BaseManageableRepository):
        super().__init__()
        self._image = image
        self._images = images

    def execute(self):
        self._images.update(self._image)


class DownloadImageFromPublicUrlUseCase(BaseUseCase):
    def __init__(
        self, project: ProjectEntity, image_url: str, image_name: str = None,
    ):
        super().__init__()
        self._project = project
        self._image_url = image_url
        self._image_name = image_name

    def validate_project_type(self):
        if self._project.upload_state == constances.UploadState.EXTERNAL.value:
            raise AppValidationException(
                "The function does not support projects containing images attached with URLs"
            )

    def execute(self):
        try:
            response = requests.get(url=self._image_url)
            if response.ok:
                import re

                content_description = response.headers.get(
                    "Content-Description", response.headers.get("Content-Disposition")
                )
                if content_description:
                    result = re.findall(
                        r"filename\*?=([^;]+)", content_description, flags=re.IGNORECASE
                    )
                else:
                    result = None
                self._response.data = (
                    io.BytesIO(response.content),
                    result[0].strip().strip('"')
                    if result
                    else str(uuid.uuid4()) + ".jpg",
                )
            else:
                raise requests.exceptions.RequestException()
        except requests.exceptions.RequestException as e:
            self._response.errors = AppException(
                f"Couldn't download image {self._image_url}, {e}"
            )
        return self._response


class ImagesBulkCopyUseCase(BaseUseCase):
    """
    Copy images in bulk between folders in a project.
    Return skipped image names.
    """

    CHUNK_SIZE = 1000

    def __init__(
        self,
        project: ProjectEntity,
        from_folder: FolderEntity,
        to_folder: FolderEntity,
        image_names: List[str],
        backend_service_provider: SuerannotateServiceProvider,
        include_annotations: bool,
        include_pin: bool,
    ):
        super().__init__()
        self._project = project
        self._from_folder = from_folder
        self._to_folder = to_folder
        self._image_names = image_names
        self._backend_service = backend_service_provider
        self._include_annotations = include_annotations
        self._include_pin = include_pin

    def validate_project_type(self):
        if self._project.project_type == constances.ProjectType.VIDEO.value:
            raise AppValidationException(
                "The function does not support projects containing videos attached with URLs"
            )

    def execute(self):
        if self.is_valid():
            images = self._backend_service.get_bulk_images(
                project_id=self._project.uuid,
                team_id=self._project.team_id,
                folder_id=self._to_folder.uuid,
                images=self._image_names,
            )
            duplications = [image["name"] for image in images]
            images_to_copy = set(self._image_names) - set(duplications)
            skipped_images = duplications
            for i in range(0, len(images_to_copy), self.CHUNK_SIZE):
                poll_id = self._backend_service.copy_images_between_folders_transaction(
                    team_id=self._project.team_id,
                    project_id=self._project.uuid,
                    from_folder_id=self._from_folder.uuid,
                    to_folder_id=self._to_folder.uuid,
                    images=self._image_names[i : i + self.CHUNK_SIZE],
                    include_annotations=self._include_annotations,
                    include_pin=self._include_pin,
                )
                if not poll_id:
                    skipped_images.append(self._image_names[i : i + self.CHUNK_SIZE])
                    continue

                await_time = len(images_to_copy) * 0.3
                timeout_start = time.time()
                while time.time() < timeout_start + await_time:
                    done_count, skipped_count = self._backend_service.get_progress(
                        self._project.uuid, self._project.team_id, poll_id
                    )
                    if done_count + skipped_count == len(images_to_copy):
                        break
                    time.sleep(4)

            self._response.data = skipped_images
        return self._response


class GetAnnotationClassesUseCase(BaseUseCase):
    def __init__(
        self, classes: BaseManageableRepository, condition: Condition = None,
    ):
        super().__init__()
        self._classes = classes
        self._condition = condition

    def execute(self):
        self._response.data = self._classes.get_all(condition=self._condition)
        return self._response


class GetSettingsUseCase(BaseUseCase):
    def __init__(self, settings: BaseManageableRepository):
        super().__init__()
        self._settings = settings

    def execute(self):
        self._response.data = self._settings.get_all()
        return self._response


class GetWorkflowsUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        annotation_classes: BaseReadOnlyRepository,
        workflows: BaseManageableRepository,
        fill_classes=True,
    ):
        super().__init__()
        self._project = project
        self._workflows = workflows
        self._annotation_classes = annotation_classes
        self._fill_classes = fill_classes

    def validate_project_type(self):
        if self._project.project_type == constances.ProjectType.VIDEO.value:
            raise AppValidationException(
                "The function does not support projects containing videos attached with URLs"
            )

    def execute(self):
        if self.is_valid():
            data = []
            workflows = self._workflows.get_all()
            for workflow in workflows:
                workflow_data = workflow.to_dict()
                if self._fill_classes:
                    annotation_classes = self._annotation_classes.get_all()
                    for annotation_class in annotation_classes:
                        annotation_class.uuid = workflow.class_id
                        workflow_data["className"] = annotation_class.name
                data.append(workflow_data)
            self._response.data = data
        return self._response


class GetProjectMetaDataUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        include_annotation_classes: bool,
        include_settings: bool,
        include_workflow: bool,
        include_contributors: bool,
        include_complete_image_count: bool,
        annotation_classes_repo: BaseManageableRepository,
        project_settings_repo: BaseManageableRepository,
        workflow_repo: BaseManageableRepository,
        projects_repo: BaseManageableRepository,
    ):
        super().__init__()
        self._project = project
        self._include_annotation_classes = include_annotation_classes
        self._include_settings = include_settings
        self._include_workflow = include_workflow
        self._annotation_classes_repo = annotation_classes_repo
        self._project_settings_repo = project_settings_repo
        self._workflow_repo = workflow_repo
        self._projects_repo = projects_repo
        self._include_contributors = include_contributors
        self._include_complete_image_count = include_complete_image_count

    def execute(self):
        res = {"project": self._project}
        if self._include_annotation_classes:
            res["annotation_classes"] = self._annotation_classes_repo.get_all()
        if self._include_settings:
            res["settings"] = self._project_settings_repo.get_all()
        if self._include_workflow:
            res["workflow"] = self._workflow_repo.get_all()
        if self._include_contributors:
            res["contributors"] = self._project.users
        if self._include_complete_image_count:
            res["project"] = self._projects_repo.get_all(
                condition=(
                    Condition("completeImagesCount", "true", EQ)
                    & Condition("name", self._project.name, EQ)
                    & Condition("team_id", self._project.team_id, EQ)
                )
            )

        self._response.data = res
        return self._response


class UpdateSettingsUseCase(BaseUseCase):
    def __init__(
        self,
        projects: BaseReadOnlyRepository,
        settings: BaseManageableRepository,
        to_update: List,
        backend_service_provider: SuerannotateServiceProvider,
        project_id: int,
        team_id: int,
    ):
        super().__init__()
        self._projects = projects
        self._settings = settings
        self._to_update = to_update
        self._backend_service_provider = backend_service_provider
        self._project_id = project_id
        self._team_id = team_id

    def validate_image_quality(self):
        for setting in self._to_update:
            if setting["attribute"].lower() == "imagequality" and isinstance(
                setting["value"], str
            ):
                setting["value"] = constances.ImageQuality.get_value(setting["value"])
                return

    def validate_project_type(self):
        project = self._projects.get_one(uuid=self._project_id, team_id=self._team_id)
        for attribute in self._to_update:
            if (
                attribute.get("attribute", "") == "ImageQuality"
                and project.project_type == constances.ProjectType.VIDEO.value
            ):
                raise AppValidationException(
                    "The function does not support projects containing videos attached with URLs"
                )

    def execute(self):
        if self.is_valid():
            old_settings = self._settings.get_all()
            attr_id_mapping = {}
            for setting in old_settings:
                attr_id_mapping[setting.attribute] = setting.uuid

            new_settings_to_update = []
            for new_setting in self._to_update:
                new_settings_to_update.append(
                    {
                        "id": attr_id_mapping[new_setting["attribute"]],
                        "attribute": new_setting["attribute"],
                        "value": new_setting["value"],
                    }
                )

            self._response.data = self._backend_service_provider.set_project_settings(
                project_id=self._project_id,
                team_id=self._team_id,
                data=new_settings_to_update,
            )
        return self._response


class DeleteImageUseCase(BaseUseCase):
    def __init__(
        self,
        images: BaseManageableRepository,
        image: ImageEntity,
        team_id: int,
        project_id: int,
    ):
        super().__init__()
        self._images = images
        self._image = image
        self._team_id = team_id
        self._project_id = project_id

    def execute(self):
        self._images.delete(self._image.uuid, self._team_id, self._project_id)
        return self._response


class GetImageMetadataUseCase(BaseUseCase):
    def __init__(
        self,
        image_name: str,
        project: ProjectEntity,
        folder: FolderEntity,
        service: SuerannotateServiceProvider,
    ):
        super().__init__()
        self._image_name = image_name
        self._project = project
        self._service = service
        self._folder = folder

    def validate_project_type(self):
        if self._project.project_type == constances.ProjectType.VIDEO.value:
            raise AppValidationException(
                "The function does not support projects containing videos attached with URLs"
            )

    def execute(self):
        if self.is_valid():
            data = self._service.get_bulk_images(
                images=[self._image_name],
                team_id=self._project.team_id,
                project_id=self._project.uuid,
                folder_id=self._folder.uuid,
            )
            if data:
                self._response.data = data[0]
            else:
                self._response.errors = AppException("Image not found.")
        return self._response


class ImagesBulkMoveUseCase(BaseUseCase):
    """
    Copy images in bulk between folders in a project.
    Return skipped image names.
    """

    CHUNK_SIZE = 1000

    def __init__(
        self,
        project: ProjectEntity,
        from_folder: FolderEntity,
        to_folder: FolderEntity,
        image_names: List[str],
        backend_service_provider: SuerannotateServiceProvider,
    ):
        super().__init__()
        self._project = project
        self._from_folder = from_folder
        self._to_folder = to_folder
        self._image_names = image_names
        self._backend_service = backend_service_provider

    def execute(self):
        moved_images = []
        for i in range(0, len(self._image_names), self.CHUNK_SIZE):
            moved_images.extend(
                self._backend_service.move_images_between_folders(
                    team_id=self._project.team_id,
                    project_id=self._project.uuid,
                    from_folder_id=self._from_folder.uuid,
                    to_folder_id=self._to_folder.uuid,
                    images=self._image_names[i : i + self.CHUNK_SIZE],  # noqa: E203
                )
            )
        self._response.data = moved_images
        return self._response


class SetImageAnnotationStatuses(BaseUseCase):
    CHUNK_SIZE = 500

    def __init__(
        self,
        service: SuerannotateServiceProvider,
        projects: BaseReadOnlyRepository,
        image_names: list,
        team_id: int,
        project_id: int,
        folder_id: int,
        images_repo: BaseManageableRepository,
        annotation_status: int,
    ):
        super().__init__()
        self._service = service
        self._projects = projects
        self._image_names = image_names
        self._team_id = team_id
        self._project_id = project_id
        self._folder_id = folder_id
        self._annotation_status = annotation_status
        self._images_repo = images_repo

    def validate_project_type(self):
        project = self._projects.get_one(uuid=self._project_id, team_id=self._team_id)
        if project.project_type == constances.ProjectType.VIDEO.value:
            raise AppValidationException(
                "The function does not support projects containing videos attached with URLs"
            )

    def execute(self):
        if self.is_valid():
            if self._image_names is None:
                condition = (
                    Condition("team_id", self._team_id, EQ)
                    & Condition("project_id", self._project_id, EQ)
                    & Condition("folder_id", self._folder_id, EQ)
                )
                self._image_names = [
                    image.name for image in self._images_repo.get_all(condition)
                ]
            for i in range(0, len(self._image_names), self.CHUNK_SIZE):
                status_changed = self._service.set_images_statuses_bulk(
                    image_names=self._image_names[
                        i : i + self.CHUNK_SIZE
                    ],  # noqa: E203
                    team_id=self._team_id,
                    project_id=self._project_id,
                    folder_id=self._folder_id,
                    annotation_status=self._annotation_status,
                )
                if not status_changed:
                    self._response.errors = AppException("Failed to change status.")
        return self._response


class DeleteImagesUseCase(BaseUseCase):
    CHUNK_SIZE = 1000

    def __init__(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        backend_service_provider: SuerannotateServiceProvider,
        images: BaseReadOnlyRepository,
        image_names: List[str] = None,
    ):
        super().__init__()
        self._project = project
        self._folder = folder
        self._images = images
        self._backend_service = backend_service_provider
        self._image_names = image_names

    def validate_project_type(self):
        if self._project.project_type == constances.ProjectType.VIDEO.value:
            raise AppValidationException(
                "The function does not support projects containing videos attached with URLs"
            )

    def execute(self):
        if self.is_valid():
            if self._image_names:
                image_ids = [
                    image.uuid
                    for image in GetBulkImages(
                        service=self._backend_service,
                        project_id=self._project.uuid,
                        team_id=self._project.team_id,
                        folder_id=self._folder.uuid,
                        images=self._image_names,
                    )
                    .execute()
                    .data
                ]
            else:
                condition = (
                    Condition("team_id", self._project.team_id, EQ)
                    & Condition("project_id", self._project.uuid, EQ)
                    & Condition("folder_id", self._folder.uuid, EQ)
                )
                image_ids = [image.uuid for image in self._images.get_all(condition)]

            for i in range(0, len(image_ids), self.CHUNK_SIZE):
                self._backend_service.delete_images(
                    project_id=self._project.uuid,
                    team_id=self._project.team_id,
                    image_ids=image_ids[i : i + self.CHUNK_SIZE],  # noqa: E203
                )
        return self._response


class AssignImagesUseCase(BaseUseCase):

    CHUNK_SIZE = 500

    def __init__(
        self,
        service: SuerannotateServiceProvider,
        project: ProjectEntity,
        folder: FolderEntity,
        image_names: list,
        user: str,
    ):
        super().__init__()
        self._project = project
        self._folder = folder
        self._image_names = image_names
        self._user = user
        self._service = service

    def validate_project_type(self):
        if self._project.project_type == constances.ProjectType.VIDEO.value:
            raise AppValidationException(
                "The function does not support projects containing videos attached with URLs"
            )

    def execute(self):
        if self.is_valid():
            for i in range(0, len(self._image_names), self.CHUNK_SIZE):
                is_assigned = self._service.assign_images(
                    team_id=self._project.team_id,
                    project_id=self._project.uuid,
                    folder_name=self._folder.name,
                    user=self._user,
                    image_names=self._image_names[
                        i : i + self.CHUNK_SIZE  # noqa: E203
                    ],
                )
                if not is_assigned:
                    self._response.errors = AppException(
                        f"Cant assign {', '.join(self._image_names[i: i + self.CHUNK_SIZE])}"
                    )
                    continue
        return self._response


class UnAssignImagesUseCase(BaseUseCase):

    CHUNK_SIZE = 500

    def __init__(
        self,
        service: SuerannotateServiceProvider,
        project_entity: ProjectEntity,
        folder: FolderEntity,
        image_names: list,
    ):
        super().__init__()
        self._project_entity = project_entity
        self._folder = folder
        self._image_names = image_names
        self._service = service

    def execute(self):
        # todo handling to backend side
        for i in range(0, len(self._image_names), self.CHUNK_SIZE):
            is_un_assigned = self._service.un_assign_images(
                team_id=self._project_entity.team_id,
                project_id=self._project_entity.uuid,
                folder_name=self._folder.name,
                image_names=self._image_names[i : i + self.CHUNK_SIZE],  # noqa: E203
            )
            if not is_un_assigned:
                self._response.errors = AppException(
                    f"Cant un assign {', '.join(self._image_names[i : i + self.CHUNK_SIZE])}"
                )

        return self._response


class UnAssignFolderUseCase(BaseUseCase):
    def __init__(
        self,
        service: SuerannotateServiceProvider,
        project_entity: ProjectEntity,
        folder: FolderEntity,
    ):
        super().__init__()
        self._service = service
        self._project_entity = project_entity
        self._folder = folder

    def execute(self):
        is_un_assigned = self._service.un_assign_folder(
            team_id=self._project_entity.team_id,
            project_id=self._project_entity.uuid,
            folder_name=self._folder.name,
        )
        if not is_un_assigned:
            self._response.errors = AppException(f"Cant un assign {self._folder.name}")
        return self._response


class AssignFolderUseCase(BaseUseCase):
    def __init__(
        self,
        service: SuerannotateServiceProvider,
        project_entity: ProjectEntity,
        folder: FolderEntity,
        users: List[str],
    ):
        super().__init__()
        self._service = service
        self._project_entity = project_entity
        self._folder = folder
        self._users = users

    def execute(self):
        is_assigned = self._service.assign_folder(
            team_id=self._project_entity.team_id,
            project_id=self._project_entity.uuid,
            folder_name=self._folder.name,
            users=self._users,
        )
        if is_assigned:
            logger.info(
                f'Assigned {self._folder.name} to users: {", ".join(self._users)}'
            )
        else:
            self._response.errors = AppException(
                f"Couldn't assign folder to users: {', '.join(self._users)}"
            )
        return self._response


class ShareProjectUseCase(BaseUseCase):
    def __init__(
        self,
        service: SuerannotateServiceProvider,
        project_entity: ProjectEntity,
        user_id: str,
        user_role: str,
    ):
        super().__init__()
        self._service = service
        self._project_entity = project_entity
        self._user_id = user_id
        self._user_role = user_role

    @property
    def user_role(self):
        return constances.UserRole.get_value(self._user_role)

    def execute(self):
        self._response.data = self._service.share_project(
            team_id=self._project_entity.team_id,
            project_id=self._project_entity.uuid,
            user_id=self._user_id,
            user_role=self.user_role,
        )
        if not self._response.errors:
            logger.info(
                f"Shared project {self._project_entity.name} with user {self._user_id} and role {constances.UserRole.get_name(self.user_role)}"
            )
        return self._response


class UnShareProjectUseCase(BaseUseCase):
    def __init__(
        self,
        service: SuerannotateServiceProvider,
        project_entity: ProjectEntity,
        user_id: str,
    ):
        super().__init__()
        self._service = service
        self._project_entity = project_entity
        self._user_id = user_id

    def execute(self):
        self._response.data = self._service.un_share_project(
            team_id=self._project_entity.team_id,
            project_id=self._project_entity.uuid,
            user_id=self._user_id,
        )
        logger.info(
            f"Unshared project {self._project_entity.name} from user ID {self._user_id}"
        )
        return self._response


class GetProjectMetadataUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        service: SuerannotateServiceProvider,
        annotation_classes: BaseManageableRepository,
        settings: BaseManageableRepository,
        workflows: BaseManageableRepository,
        projects: BaseManageableRepository,
        include_annotation_classes: bool,
        include_settings: bool,
        include_workflow: bool,
        include_contributors: bool,
        include_complete_image_count: bool,
    ):
        super().__init__()
        self._project = project
        self._service = service

        self._annotation_classes = annotation_classes
        self._settings = settings
        self._workflows = workflows
        self._projects = projects

        self._include_annotation_classes = include_annotation_classes
        self._include_settings = include_settings
        self._include_workflow = include_workflow
        self._include_contributors = include_contributors
        self._include_complete_image_count = include_complete_image_count

    @property
    def annotation_classes_use_case(self):
        return GetAnnotationClassesUseCase(classes=self._annotation_classes)

    @property
    def settings_use_case(self):
        return GetSettingsUseCase(settings=self._settings)

    @property
    def work_flow_use_case(self):
        return GetWorkflowsUseCase(
            project=self._project,
            workflows=self._workflows,
            annotation_classes=self._annotation_classes,
        )

    def execute(self):
        data = {}
        project = self._projects.get_one(
            uuid=self._project.uuid, team_id=self._project.team_id
        )
        data["project"] = project
        if self._include_complete_image_count:
            projects = self._projects.get_all(
                condition=(
                    Condition("completeImagesCount", "true", EQ)
                    & Condition("name", self._project.name, EQ)
                    & Condition("team_id", self._project.team_id, EQ)
                )
            )
            if projects:
                data["project"] = projects[0]

        if self._include_annotation_classes:
            self.annotation_classes_use_case.execute()
            data["classes"] = self.annotation_classes_use_case.execute().data

        if self._include_settings:
            self.settings_use_case.execute()
            data["settings"] = self.settings_use_case.execute().data

        if self._include_workflow:
            self.work_flow_use_case.execute()
            data["workflows"] = self.work_flow_use_case.execute().data

        if self._include_contributors:
            data["contributors"] = project.users
        else:
            project.users = []

        self._response.data = data
        return self._response


class GetImageAnnotationsUseCase(BaseUseCase):
    def __init__(
        self,
        service: SuerannotateServiceProvider,
        project: ProjectEntity,
        folder: FolderEntity,
        image_name: str,
        images: BaseManageableRepository,
    ):
        super().__init__()
        self._service = service
        self._project = project
        self._folder = folder
        self._image_name = image_name
        self._images = images

    @property
    def image_use_case(self):
        use_case = GetImageUseCase(
            project=self._project,
            folder=self._folder,
            image_name=self._image_name,
            images=self._images,
            service=self._service,
        )
        return use_case

    def validate_project_type(self):
        if self._project.project_type == constances.ProjectType.VIDEO.value:
            raise AppValidationException(
                "The function does not support projects containing videos attached with URLs"
            )

    def execute(self):
        if self.is_valid():
            data = {
                "annotation_json": None,
                "annotation_json_filename": None,
                "annotation_mask": None,
                "annotation_mask_filename": None,
            }
            image_response = self.image_use_case.execute()
            token = self._service.get_download_token(
                project_id=self._project.uuid,
                team_id=self._project.team_id,
                folder_id=self._folder.uuid,
                image_id=image_response.data.uuid,
            )
            credentials = token["annotations"]["MAIN"][0]
            if self._project.project_type == constances.ProjectType.VECTOR.value:
                file_postfix = "___objects.json"
            else:
                file_postfix = "___pixel.json"
                data["annotation_mask_filename"] = f"{self._image_name}___save.png"
            data["annotation_json_filename"] = f"{self._image_name}{file_postfix}"

            response = requests.get(
                url=credentials["annotation_json_path"]["url"],
                headers=credentials["annotation_json_path"]["headers"],
            )
            if not response.ok:
                logger.warning("Couldn't load annotations.")
                self._response.data = data
                return self._response
            data["annotation_json"] = response.json()
            data["annotation_json_filename"] = f"{self._image_name}{file_postfix}"
            if self._project.project_type == constances.ProjectType.PIXEL.value:
                annotation_blue_map_creds = credentials["annotation_bluemap_path"]
                response = requests.get(
                    url=annotation_blue_map_creds["url"],
                    headers=annotation_blue_map_creds["headers"],
                )
                data["annotation_mask"] = io.BytesIO(response.content)

            self._response.data = data

        return self._response


class GetS3ImageUseCase(BaseUseCase):
    def __init__(
        self, s3_bucket, image_path: str,
    ):
        super().__init__()
        self._s3_bucket = s3_bucket
        self._image_path = image_path

    def execute(self):
        image = io.BytesIO()
        session = boto3.Session()
        resource = session.resource("s3")
        image_object = resource.Object(self._s3_bucket, self._image_path)
        if image_object.content_length > constances.MAX_IMAGE_SIZE:
            raise AppValidationException(f"File size is {image_object.content_length}")
        image_object.download_fileobj(image)
        self._response.data = image
        return self._response


class GetImagePreAnnotationsUseCase(BaseUseCase):
    def __init__(
        self,
        service: SuerannotateServiceProvider,
        project: ProjectEntity,
        folder: FolderEntity,
        image_name: str,
        images: BaseManageableRepository,
    ):
        super().__init__()
        self._service = service
        self._project = project
        self._folder = folder
        self._image_name = image_name
        self._images = images

    @property
    def image_use_case(self):
        return GetImageUseCase(
            project=self._project,
            folder=self._folder,
            image_name=self._image_name,
            images=self._images,
            service=self._service,
        )

    def validate_project_type(self):
        if self._project.project_type == constances.ProjectType.VIDEO.value:
            raise AppValidationException(
                "The function does not support projects containing videos attached with URLs"
            )

    def execute(self):
        data = {
            "preannotation_json": None,
            "preannotation_json_filename": None,
            "preannotation_mask": None,
            "preannotation_mask_filename": None,
        }
        image_response = self.image_use_case.execute()
        token = self._service.get_download_token(
            project_id=self._project.uuid,
            team_id=self._project.team_id,
            folder_id=self._folder.uuid,
            image_id=image_response.data.uuid,
        )
        credentials = token["annotations"]["PREANNOTATION"][0]
        annotation_json_creds = credentials["annotation_json_path"]
        if self._project.project_type == constances.ProjectType.VECTOR.value:
            file_postfix = "___objects.json"
        else:
            file_postfix = "___pixel.json"

        response = requests.get(
            url=annotation_json_creds["url"], headers=annotation_json_creds["headers"],
        )
        if not response.ok:
            raise AppException("Couldn't load annotations.")
        data["preannotation_json"] = response.json()
        data["preannotation_json_filename"] = f"{self._image_name}{file_postfix}"
        if self._project.project_type == constances.ProjectType.PIXEL.value:
            annotation_blue_map_creds = credentials["annotation_bluemap_path"]
            response = requests.get(
                url=annotation_blue_map_creds["url"],
                headers=annotation_blue_map_creds["headers"],
            )
            data["preannotation_mask"] = io.BytesIO(response.content)
            data["preannotation_mask_filename"] = f"{self._image_name}___save.png"

        self._response.data = data
        return self._response


class DownloadImageAnnotationsUseCase(BaseUseCase):
    def __init__(
        self,
        service: SuerannotateServiceProvider,
        project: ProjectEntity,
        folder: FolderEntity,
        image_name: str,
        images: BaseManageableRepository,
        destination: str,
    ):
        super().__init__()
        self._service = service
        self._project = project
        self._folder = folder
        self._image_name = image_name
        self._images = images
        self._destination = destination

    @property
    def image_use_case(self):
        return GetImageUseCase(
            service=self._service,
            project=self._project,
            folder=self._folder,
            image_name=self._image_name,
            images=self._images,
        )

    def validate_project_type(self):
        if self._project.project_type == constances.ProjectType.VIDEO.value:
            raise AppValidationException(
                "The function does not support projects containing videos attached with URLs"
            )

    def execute(self):
        if self.is_valid():
            data = {
                "annotation_json": None,
                "annotation_json_filename": None,
                "annotation_mask": None,
                "annotation_mask_filename": None,
            }
            image_response = self.image_use_case.execute()
            token = self._service.get_download_token(
                project_id=self._project.uuid,
                team_id=self._project.team_id,
                folder_id=self._folder.uuid,
                image_id=image_response.data.uuid,
            )
            credentials = token["annotations"]["MAIN"][0]

            annotation_json_creds = credentials["annotation_json_path"]
            if self._project.project_type == constances.ProjectType.VECTOR.value:
                file_postfix = "___objects.json"
            else:
                file_postfix = "___pixel.json"

            response = requests.get(
                url=annotation_json_creds["url"],
                headers=annotation_json_creds["headers"],
            )
            if not response.ok:
                logger.warning("Couldn't load annotations.")
                self._response.data = (None, None)
                return self._response
            data["annotation_json"] = response.json()
            data["annotation_json_filename"] = f"{self._image_name}{file_postfix}"
            mask_path = None
            if self._project.project_type == constances.ProjectType.PIXEL.value:
                annotation_blue_map_creds = credentials["annotation_bluemap_path"]
                response = requests.get(
                    url=annotation_blue_map_creds["url"],
                    headers=annotation_blue_map_creds["headers"],
                )
                data["annotation_mask"] = io.BytesIO(response.content)
                data["annotation_mask_filename"] = f"{self._image_name}___save.png"
                mask_path = Path(self._destination) / data["annotation_mask_filename"]
                with open(mask_path, "wb") as f:
                    f.write(data["annotation_mask"].getbuffer())

            json_path = Path(self._destination) / data["annotation_json_filename"]
            with open(json_path, "w") as f:
                json.dump(data["annotation_json"], f, indent=4)

            self._response.data = (str(json_path), str(mask_path))
        return self._response


class DownloadImagePreAnnotationsUseCase(BaseUseCase):
    def __init__(
        self,
        service: SuerannotateServiceProvider,
        project: ProjectEntity,
        folder: FolderEntity,
        image_name: str,
        images: BaseManageableRepository,
        destination: str,
    ):
        super().__init__()
        self._service = service
        self._project = project
        self._folder = folder
        self._image_name = image_name
        self._image_response = Response()
        self._images = images
        self._destination = destination

    @property
    def image_use_case(self):
        return GetImageUseCase(
            project=self._project,
            folder=self._folder,
            image_name=self._image_name,
            images=self._images,
            service=self._service,
        )

    def execute(self):
        data = {
            "preannotation_json": None,
            "preannotation_json_filename": None,
            "preannotation_mask": None,
            "preannotation_mask_filename": None,
        }
        image_response = self.image_use_case.execute()
        token = self._service.get_download_token(
            project_id=self._project.uuid,
            team_id=self._project.team_id,
            folder_id=self._folder.uuid,
            image_id=image_response.data.uuid,
        )
        credentials = token["annotations"]["PREANNOTATION"][0]
        annotation_json_creds = credentials["annotation_json_path"]
        if self._project.project_type == constances.ProjectType.VECTOR.value:
            file_postfix = "___objects.json"
        else:
            file_postfix = "___pixel.json"

        response = requests.get(
            url=annotation_json_creds["url"], headers=annotation_json_creds["headers"],
        )
        if not response.ok:
            raise AppException("Couldn't load annotations.")
        data["preannotation_json"] = response.json()
        data["preannotation_json_filename"] = f"{self._image_name}{file_postfix}"
        mask_path = None
        if self._project.project_type == constances.ProjectType.PIXEL.value:
            annotation_blue_map_creds = credentials["annotation_bluemap_path"]
            response = requests.get(
                url=annotation_blue_map_creds["url"],
                headers=annotation_blue_map_creds["headers"],
            )
            data["preannotation_mask"] = io.BytesIO(response.content)
            data["preannotation_mask_filename"] = f"{self._image_name}___save.png"
            mask_path = Path(self._destination) / data["preannotation_mask_filename"]
            with open(mask_path, "wb") as f:
                f.write(data["preannotation_mask"].getbuffer())

        json_path = Path(self._destination) / data["preannotation_json_filename"]
        with open(json_path, "w") as f:
            json.dump(data["preannotation_json"], f, indent=4)

            self._response.data = (str(json_path), str(mask_path))
        return self._response


class GetExportsUseCase(BaseUseCase):
    def __init__(
        self,
        service: SuerannotateServiceProvider,
        project: ProjectEntity,
        return_metadata: bool = False,
    ):
        super().__init__()
        self._service = service
        self._project = project
        self._return_metadata = return_metadata

    def execute(self):
        data = self._service.get_exports(
            team_id=self._project.team_id, project_id=self._project.uuid
        )
        self._response.data = data
        if not self._return_metadata:
            self._response.data = [i["name"] for i in data]
        return self._response


class UploadS3ImagesBackendUseCase(BaseUseCase):
    def __init__(
        self,
        backend_service_provider: SuerannotateServiceProvider,
        settings: BaseReadOnlyRepository,
        project: ProjectEntity,
        folder: FolderEntity,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        folder_path: str,
        image_quality: str,
    ):
        super().__init__()
        self._backend_service = backend_service_provider
        self._settings = settings
        self._project = project
        self._folder = folder
        self._access_key = access_key
        self._secret_key = secret_key
        self._bucket_name = bucket_name
        self._folder_path = folder_path
        self._image_quality = image_quality

    def validate_image_quality(self):
        if self._image_quality and self._image_quality not in (
            "compressed",
            "original",
        ):
            raise AppValidationException("Invalid value for image_quality")

    def execute(self):
        old_setting = None
        if self._image_quality:
            settings = self._settings.get_all()
            for setting in settings:
                if setting.attribute == "ImageQuality":
                    if setting.value == "compressed":
                        setting.value = 60
                    else:
                        setting.value = 100
                    self._backend_service.set_project_settings(
                        project_id=self._project.uuid,
                        team_id=self._project.team_id,
                        data=[setting.to_dict()],
                    )
                    break
            else:
                raise AppException("Cant find settings.")

        response = self._backend_service.upload_form_s3(
            project_id=self._project.uuid,
            team_id=self._project.team_id,
            access_key=self._access_key,
            secret_key=self._secret_key,
            bucket_name=self._bucket_name,
            from_folder_name=self._folder_path,
            to_folder_id=self._folder.uuid,
        )

        if not response.ok:
            self._response.errors = AppException(response.json()["error"])

        in_progress = response.ok
        if in_progress:
            while True:
                time.sleep(4)
                progress = self._backend_service.get_upload_status(
                    project_id=self._project.uuid,
                    team_id=self._project.team_id,
                    folder_id=self._folder.uuid,
                )
                if progress == "2":
                    break
                elif progress != "1":
                    raise AppException("Couldn't upload to project from S3.")

        if old_setting:
            self._backend_service.set_project_settings(
                project_id=self._project.uuid,
                team_id=self._project.team_id,
                data=[old_setting.to_dict()],
            )
        return self._response


class GetProjectImageCountUseCase(BaseUseCase):
    def __init__(
        self,
        service: SuerannotateServiceProvider,
        project: ProjectEntity,
        folder: FolderEntity,
        with_all_sub_folders: bool = False,
    ):
        super().__init__()
        self._service = service
        self._project = project
        self._folder = folder
        self._with_all_sub_folders = with_all_sub_folders

    def validate_user_input(self):
        if not self._folder.name == "root" and self._with_all_sub_folders:
            raise AppValidationException("The folder does not contain any sub-folders.")

    def validate_project_type(self):
        if self._project.project_type == constances.ProjectType.VIDEO.value:
            raise AppValidationException(
                "The function does not support projects containing videos attached with URLs"
            )

    def execute(self):
        if self.is_valid():
            data = self._service.get_project_images_count(
                project_id=self._project.uuid, team_id=self._project.team_id
            )
            count = 0
            if self._folder.name == "root":
                count += data["images"]["count"]
                if self._with_all_sub_folders:
                    for i in data["folders"]["data"]:
                        count += i["imagesCount"]
            else:
                for i in data["folders"]["data"]:
                    if i["id"] == self._folder.uuid:
                        count = i["imagesCount"]

            self._response.data = count
        return self._response


class ExtractFramesUseCase(BaseUseCase):
    def __init__(
        self,
        backend_service_provider: SuerannotateServiceProvider,
        project: ProjectEntity,
        folder: FolderEntity,
        video_path: str,
        extract_path: str,
        start_time: float,
        end_time: float = None,
        target_fps: float = None,
        annotation_status_code: int = constances.AnnotationStatus.NOT_STARTED.value,
        image_quality_in_editor: str = None,
        limit: int = None,
    ):
        super().__init__()
        self._backend_service = backend_service_provider
        self._project = project
        self._folder = folder
        self._video_path = video_path
        self._extract_path = extract_path
        self._start_time = start_time
        self._end_time = end_time
        self._target_fps = target_fps
        self._annotation_status_code = annotation_status_code
        self._image_quality_in_editor = image_quality_in_editor
        self._limit = limit
        self._auth_data = None

    def validate_auth_data(self):
        response = self._backend_service.get_s3_upload_auth_token(
            team_id=self._project.team_id,
            folder_id=self._folder.uuid,
            project_id=self._project.uuid,
        )
        if "error" in response:
            raise AppException(response.get("error"))
        self._auth_data = response

    @property
    def upload_auth_data(self):
        return self._auth_data

    @property
    def limit(self):
        if not self._limit:
            return self.upload_auth_data.get("availableImageCount")
        return self._limit

    def execute(self):
        if self.is_valid():
            extracted_paths = VideoPlugin.extract_frames(
                video_path=self._video_path,
                start_time=self._start_time,
                end_time=self._end_time,
                extract_path=self._extract_path,
                limit=self.limit,
                target_fps=self._target_fps,
            )
            self._response.data = extracted_paths
        return self._response


class CreateAnnotationClassUseCase(BaseUseCase):
    def __init__(
        self,
        annotation_classes: BaseManageableRepository,
        annotation_class: AnnotationClassEntity,
        project_name: str,
    ):
        super().__init__()
        self._annotation_classes = annotation_classes
        self._annotation_class = annotation_class
        self._project_name = project_name

    def validate_uniqueness(self):
        annotation_classes = self._annotation_classes.get_all(
            Condition("name", self._annotation_class.name, EQ)
        )
        if any(
            [
                True
                for annotation_class in annotation_classes
                if annotation_class.name == self._annotation_class.name
            ]
        ):
            raise AppValidationException("Annotation class already exits.")

    def execute(self):
        if self.is_valid():
            logger.info(
                "Creating annotation class in project %s with name %s",
                self._project_name,
                self._annotation_class.name,
            )
            created = self._annotation_classes.insert(entity=self._annotation_class)
            self._response.data = created
        else:
            self._response.data = self._annotation_class
        return self._response


class DeleteAnnotationClassUseCase(BaseUseCase):
    def __init__(
        self,
        annotation_classes_repo: BaseManageableRepository,
        annotation_class_name: str,
        project_name: str,
    ):
        super().__init__()
        self._annotation_classes_repo = annotation_classes_repo
        self._annotation_class_name = annotation_class_name
        self._annotation_class = None
        self._project_name = project_name

    @property
    def uuid(self):
        if self._annotation_class:
            return self._annotation_class.uuid

    def execute(self):
        annotation_classes = self._annotation_classes_repo.get_all(
            condition=Condition("name", self._annotation_class_name, EQ)
            & Condition("pattern", True, EQ)
        )
        self._annotation_class = annotation_classes[0]
        logger.info(
            "Deleting annotation class from project %s with name %s",
            self._project_name,
            self._annotation_class_name,
        )
        self._annotation_classes_repo.delete(uuid=self.uuid)


class GetAnnotationClassUseCase(BaseUseCase):
    def __init__(
        self,
        annotation_classes_repo: BaseManageableRepository,
        annotation_class_name: str,
    ):
        super().__init__()
        self._annotation_classes_repo = annotation_classes_repo
        self._annotation_class_name = annotation_class_name

    def execute(self):
        classes = self._annotation_classes_repo.get_all(
            condition=Condition("name", self._annotation_class_name, EQ)
        )
        self._response.data = classes[0]
        return self._response


class DownloadAnnotationClassesUseCase(BaseUseCase):
    def __init__(
        self,
        annotation_classes_repo: BaseManageableRepository,
        download_path: str,
        project_name: str,
    ):
        super().__init__()
        self._annotation_classes_repo = annotation_classes_repo
        self._download_path = download_path
        self._project_name = project_name

    def execute(self):
        logger.info(
            "Downloading classes.json from project %s to folder %s.",
            self._project_name,
            str(self._download_path),
        )
        classes = self._annotation_classes_repo.get_all()
        classes = [entity.to_dict() for entity in classes]
        json.dump(
            classes, open(Path(self._download_path) / "classes.json", "w"), indent=4
        )
        self._response.data = self._download_path
        return self._response


class CreateAnnotationClassesUseCase(BaseUseCase):

    CHUNK_SIZE = 500

    def __init__(
        self,
        service: SuerannotateServiceProvider,
        annotation_classes_repo: BaseManageableRepository,
        annotation_classes: list,
        project: ProjectEntity,
    ):
        super().__init__()
        self._service = service
        self._annotation_classes_repo = annotation_classes_repo
        self._annotation_classes = annotation_classes
        self._project = project

    def execute(self):
        existing_annotation_classes = self._annotation_classes_repo.get_all()
        existing_classes_name = [i.name for i in existing_annotation_classes]
        unique_annotation_classes = []
        for annotation_class in self._annotation_classes:
            if annotation_class["name"] in existing_classes_name:
                logger.warning(
                    "Annotation class %s already in project. Skipping.",
                    annotation_class["name"],
                )
                continue
            else:
                unique_annotation_classes.append(annotation_class)

        created = []

        for i in range(0, len(unique_annotation_classes), self.CHUNK_SIZE):
            created += self._service.set_annotation_classes(
                project_id=self._project.uuid,
                team_id=self._project.team_id,
                data=unique_annotation_classes[i : i + self.CHUNK_SIZE],
            )
        self._response.data = created
        return self._response


class SetWorkflowUseCase(BaseUseCase):
    def __init__(
        self,
        service: SuerannotateServiceProvider,
        annotation_classes_repo: BaseManageableRepository,
        workflow_repo: BaseManageableRepository,
        steps: list,
        project: ProjectEntity,
    ):
        super().__init__()
        self._service = service
        self._annotation_classes_repo = annotation_classes_repo
        self._workflow_repo = workflow_repo
        self._steps = steps
        self._project = project

    def validate_project_type(self):
        if self._project.project_type == constances.ProjectType.VIDEO.value:
            raise AppValidationException(
                "The function does not support projects containing videos attached with URLs"
            )

    def execute(self):
        if self.is_valid():
            annotation_classes = self._annotation_classes_repo.get_all()
            annotation_classes_map = {}
            annotations_classes_attributes_map = {}
            for annnotation_class in annotation_classes:
                annotation_classes_map[annnotation_class.name] = annnotation_class.uuid
                for attribute_group in annnotation_class.attribute_groups:
                    for attribute in attribute_group["attributes"]:
                        annotations_classes_attributes_map[
                            f"{annnotation_class.name}__{attribute_group['name']}__{attribute['name']}"
                        ] = attribute["id"]

            for step in [step for step in self._steps if "className" in step]:
                if step.get("id"):
                    del step["id"]
                step["class_id"] = annotation_classes_map.get(step["className"], None)
                if not step["class_id"]:
                    raise AppException(
                        "Annotation class not found in set_project_workflow."
                    )

            self._service.set_project_workflow_bulk(
                team_id=self._project.team_id,
                project_id=self._project.uuid,
                steps=self._steps,
            )
            existing_workflows = self._workflow_repo.get_all()
            existing_workflows_map = {}
            for workflow in existing_workflows:
                existing_workflows_map[workflow.step] = workflow.uuid

            req_data = []
            for step in self._steps:
                annotation_class_name = step["className"]
                for attribute in step["attribute"]:
                    attribute_name = attribute["attribute"]["name"]
                    attribute_group_name = attribute["attribute"]["attribute_group"][
                        "name"
                    ]
                    if not annotations_classes_attributes_map.get(
                        f"{annotation_class_name}__{attribute_group_name}__{attribute_name}",
                        None,
                    ):
                        raise AppException(
                            "Attribute group name or attribute name not found in set_project_workflow."
                        )

                    if not existing_workflows_map.get(step["step"], None):
                        raise AppException("Couldn't find step in workflow")

                    req_data.append(
                        {
                            "workflow_id": existing_workflows_map[step["step"]],
                            "attribute_id": annotations_classes_attributes_map[
                                f"{annotation_class_name}__{attribute_group_name}__{attribute_name}"
                            ],
                        }
                    )

            self._service.set_project_workflow_attributes_bulk(
                project_id=self._project.uuid,
                team_id=self._project.team_id,
                attributes=req_data,
            )
        return self._response


class CreateFuseImageUseCase(BaseUseCase):
    TRANSPARENCY = 128

    def __init__(
        self,
        project_type: str,
        image_path: str,
        classes: list = None,
        in_memory: bool = False,
        generate_overlay: bool = False,
    ):
        super().__init__()
        self._project_type = project_type
        self._image_path = image_path
        self._annotations = None
        self._classes = classes
        self._annotation_mask_path = None
        self._in_memory = in_memory
        self._generate_overlay = generate_overlay

    @staticmethod
    def generate_color(value: str = None):
        if not value:
            return (
                random.randint(1, 255),
                random.randint(1, 255),
                random.randint(1, 255),
            )
        return tuple(int(value.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))

    @property
    def annotations(self):
        if not self._annotations:
            image_path = (
                f"{Path(self._image_path).parent}/{Path(self._image_path).name}"
            )
            if self._project_type.upper() == constances.ProjectType.PIXEL.name.upper():
                self._annotations = json.load(open(f"{image_path}___pixel.json"))
            else:
                self._annotations = json.load(open(f"{image_path}___objects.json"))
        return self._annotations

    @property
    def blue_mask_path(self):
        image_path = Path(self._image_path)
        if self._project_type.upper() == constances.ProjectType.PIXEL.name.upper():
            self._annotation_mask_path = str(
                image_path.parent / f"{image_path.name}___save.png"
            )
        else:
            raise AppException("Vector project doesn't have blue mask.")

        return self._annotation_mask_path

    def execute(self):
        with open(self._image_path, "rb") as file:
            class_color_map = {}
            Image = namedtuple("Image", ["type", "path", "content"])
            for annotation_class in self._classes:
                class_color_map[annotation_class["name"]] = self.generate_color(
                    annotation_class["color"]
                )
            if self._project_type.upper() == constances.ProjectType.VECTOR.name.upper():
                image = ImagePlugin(io.BytesIO(file.read()))

                images = [
                    Image("fuse", f"{self._image_path}___fuse.png", image.get_empty(),)
                ]
                if self._generate_overlay:
                    images.append(
                        Image("overlay", f"{self._image_path}___overlay.png", image)
                    )

                outline_color = 4 * (255,)
                for instance in self.annotations["instances"]:
                    color = class_color_map.get(instance["className"])
                    if not color:
                        class_color_map[instance["className"]] = self.generate_color()
                    fill_color = (
                        *class_color_map[instance["className"]],
                        self.TRANSPARENCY,
                    )
                    for image in images:
                        if instance["type"] == "bbox":
                            image.content.draw_bbox(
                                **instance["points"],
                                fill_color=fill_color,
                                outline_color=outline_color,
                            )
                        elif instance["type"] == "polygon":
                            image.content.draw_polygon(
                                instance["points"],
                                fill_color=fill_color,
                                outline_color=outline_color,
                            )
                        elif instance["type"] == "ellipse":
                            image.content.draw_ellipse(
                                instance["cx"],
                                instance["cy"],
                                instance["rx"],
                                instance["ry"],
                                fill_color=fill_color,
                                outline_color=outline_color,
                            )
                        elif instance["type"] == "polyline":
                            image.content.draw_polyline(
                                points=instance["points"], fill_color=fill_color
                            )
                        elif instance["type"] == "point":
                            image.content.draw_point(
                                x=instance["x"],
                                y=instance["y"],
                                fill_color=fill_color,
                                outline_color=outline_color,
                            )
                        elif instance["type"] == "template":
                            point_set = instance["points"]
                            points_id_map = {}
                            for points in point_set:
                                points_id_map[points["id"]] = (points["x"], points["y"])
                                points = (
                                    points["x"] - 2,
                                    points["y"] - 2,
                                    points["x"] + 2,
                                    points["y"] + 2,
                                )
                                image.content.draw_ellipse(
                                    *points, fill_color, fill_color
                                )
                            for connection in instance["connections"]:
                                image.content.draw_line(
                                    points_id_map[connection["from"]],
                                    points_id_map[connection["to"]],
                                    fill_color=fill_color,
                                )
            else:
                image = ImagePlugin(io.BytesIO(file.read()))
                annotation_mask = np.array(
                    ImagePlugin(
                        io.BytesIO(open(self.blue_mask_path, "rb").read())
                    ).content
                )
                weight, height = image.get_size()
                empty_image_arr = np.full((height, weight, 4), [0, 0, 0, 255], np.uint8)
                for annotation in self.annotations["instances"]:
                    fill_color = *class_color_map[annotation["className"]], 255
                    for part in annotation["parts"]:
                        part_color = *self.generate_color(part["color"]), 255
                        temp_mask = np.alltrue(annotation_mask == part_color, axis=2)
                        empty_image_arr[temp_mask] = fill_color

                images = [
                    Image(
                        "fuse",
                        f"{self._image_path}___fuse.png",
                        ImagePlugin.from_array(empty_image_arr),
                    )
                ]

                fuse_image = ImagePlugin.from_array(empty_image_arr)
                if self._generate_overlay:
                    alpha = 0.5  # transparency measure
                    overlay = copy.copy(empty_image_arr)
                    overlay[:, :, :3] = np.array(image.content)
                    overlay = ImagePlugin.from_array(
                        cv2.addWeighted(fuse_image, alpha, overlay, 1 - alpha, 0)
                    )
                    images.append(
                        Image("overlay", f"{self._image_path}___overlay.png", overlay)
                    )

            if not self._in_memory:
                paths = []
                for image in images:
                    image.content.save(image.path)
                    paths.append(image.path)
                self._response.data = paths
            else:
                self._response.data = (image.content for image in images)
        return self._response


class DownloadImageUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        image: ImageEntity,
        images: BaseManageableRepository,
        classes: BaseManageableRepository,
        backend_service_provider: SuerannotateServiceProvider,
        download_path: str,
        image_variant: str = "original",
        include_annotations: bool = False,
        include_fuse: bool = False,
        include_overlay: bool = False,
    ):
        super().__init__()
        self._project = project
        self._image = image
        self._download_path = download_path
        self._image_variant = image_variant
        self._include_fuse = include_fuse
        self._include_overlay = include_overlay
        self._include_annotations = include_annotations
        self.get_image_use_case = GetImageBytesUseCase(
            image=image,
            backend_service_provider=backend_service_provider,
            image_variant=image_variant,
        )
        self.download_annotation_use_case = DownloadImageAnnotationsUseCase(
            service=backend_service_provider,
            project=project,
            folder=folder,
            image_name=self._image.name,
            images=images,
            destination=download_path,
        )
        self.get_annotation_classes_ues_case = GetAnnotationClassesUseCase(
            classes=classes,
        )

    def validate_project_type(self):
        if self._project.project_type == constances.ProjectType.VIDEO.value:
            raise AppValidationException(
                "The function does not support projects containing videos attached with URLs"
            )

    def validate_variant_type(self):
        if self._image_variant not in ["original", "lores"]:
            raise AppValidationException(
                "Image download variant should be either original or lores"
            )

    def validate_download_path(self):
        if not Path(str(self._download_path)).is_dir():
            raise AppValidationException(
                f"local_dir_path {self._download_path} is not an existing directory"
            )

    def validate_include_annotations(self):
        if (
            self._include_fuse or self._include_overlay
        ) and not self._include_annotations:
            raise AppValidationException(
                "To download fuse or overlay image need to set include_annotations=True in download_image"
            )

    def execute(self):
        if self.is_valid():
            self.get_image_use_case.execute()
            image_bytes = self.get_image_use_case.execute().data
            download_path = f"{self._download_path}/{self._image.name}"
            if self._image_variant == "lores":
                download_path = download_path + "___lores.jpg"
            with open(download_path, "wb") as image_file:
                image_file.write(image_bytes.getbuffer())

            annotations = None
            if self._include_annotations:
                annotations = self.download_annotation_use_case.execute().data

            fuse_image = None
            if self._include_annotations and self._include_fuse:
                classes = self.get_annotation_classes_ues_case.execute().data
                fuse_image_use_case = CreateFuseImageUseCase(
                    project_type=constances.ProjectType.get_name(
                        self._project.project_type
                    ),
                    image_path=download_path,
                    classes=[
                        annotation_class.to_dict() for annotation_class in classes
                    ],
                    generate_overlay=self._include_overlay,
                )
                fuse_image = fuse_image_use_case.execute().data

            self._response.data = (
                download_path,
                annotations,
                fuse_image,
            )
            logger.info(
                "Downloaded image %s to %s.", self._image.name, str(download_path)
            )

        return self._response


class UploadImageAnnotationsUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        annotation_classes: BaseReadOnlyRepository,
        image_name: str,
        annotations: dict,
        backend_service_provider: SuerannotateServiceProvider,
        mask=None,
        verbose: bool = True,
    ):
        super().__init__()
        self._project = project
        self._folder = folder
        self._backend_service = backend_service_provider
        self._annotation_classes = annotation_classes
        self._image_name = image_name
        self._annotations = annotations
        self._mask = mask
        self._verbose = verbose

    def validate_project_type(self):
        if self._project.project_type == constances.ProjectType.VIDEO.value:
            raise AppValidationException(
                "The function does not support projects containing videos attached with URLs"
            )

    @property
    def annotation_classes_name_map(self) -> dict:
        classes_data = defaultdict(dict)
        annotation_classes = self._annotation_classes.get_all()
        for annotation_class in annotation_classes:
            class_info = {"id": annotation_class.uuid}
            if annotation_class.attribute_groups:
                for attribute_group in annotation_class.attribute_groups:
                    attribute_group_data = defaultdict(dict)
                    for attribute in attribute_group["attributes"]:
                        attribute_group_data[attribute["name"]] = attribute["id"]
                    class_info["attribute_groups"] = {
                        attribute_group["name"]: {
                            "id": attribute_group["id"],
                            "attributes": attribute_group_data,
                        }
                    }
            classes_data[annotation_class.name] = class_info
        return classes_data

    def get_templates_mapping(self):
        templates = self._backend_service.get_templates(
            team_id=self._project.team_id
        ).get("data", [])
        templates_map = {}
        for template in templates:
            templates_map[template["name"]] = template["id"]
        return templates_map

    def fill_classes_data(self, annotations: dict):
        annotation_classes = self.annotation_classes_name_map
        if "instances" not in annotations:
            return
        unknown_classes = {}
        for annotation in [i for i in annotations["instances"] if "className" in i]:
            if "className" not in annotation:
                return
            annotation_class_name = annotation["className"]
            if annotation_class_name not in annotation_classes:
                if annotation_class_name not in unknown_classes:
                    unknown_classes[annotation_class_name] = {
                        "id": -(len(unknown_classes) + 1),
                        "attribute_groups": {},
                    }
        annotation_classes.update(unknown_classes)
        templates = self.get_templates_mapping()
        for annotation in (
            i for i in annotations["instances"] if i.get("type", None) == "template"
        ):
            annotation["templateId"] = templates.get(
                annotation.get("templateName", ""), -1
            )

        for annotation in [i for i in annotations["instances"] if "className" in i]:
            annotation_class_name = annotation["className"]
            if annotation_class_name not in annotation_classes:
                continue
            annotation["classId"] = annotation_classes[annotation_class_name]["id"]
            for attribute in annotation["attributes"]:
                if (
                    attribute["groupName"]
                    not in annotation_classes[annotation_class_name]["attribute_groups"]
                ):
                    continue
                attribute["groupId"] = annotation_classes[annotation_class_name][
                    "attribute_groups"
                ][attribute["groupName"]]["id"]
                if (
                    attribute["name"]
                    not in annotation_classes[annotation_class_name][
                        "attribute_groups"
                    ][attribute["groupName"]]["attributes"]
                ):
                    del attribute["groupId"]
                    continue
                attribute["id"] = annotation_classes[annotation_class_name][
                    "attribute_groups"
                ][attribute["groupName"]]["attributes"]

    def execute(self):
        if self.is_valid():
            image_data = self._backend_service.get_bulk_images(
                images=[self._image_name],
                folder_id=self._folder.uuid,
                team_id=self._project.team_id,
                project_id=self._project.uuid,
            )[0]
            auth_data = self._backend_service.get_annotation_upload_data(
                project_id=self._project.uuid,
                team_id=self._project.team_id,
                folder_id=self._folder.uuid,
                image_ids=[image_data["id"]],
            )
            session = boto3.Session(
                aws_access_key_id=auth_data["creds"]["accessKeyId"],
                aws_secret_access_key=auth_data["creds"]["secretAccessKey"],
                aws_session_token=auth_data["creds"]["sessionToken"],
                region_name=auth_data["creds"]["region"],
            )
            resource = session.resource("s3")
            bucket = resource.Bucket(auth_data["creds"]["bucket"])
            self.fill_classes_data(self._annotations)
            bucket.put_object(
                Key=auth_data["images"][str(image_data["id"])]["annotation_json_path"],
                Body=json.dumps(self._annotations),
            )
            if self._verbose:
                logger.info(
                    "Uploading annotations for image %s in project %s.",
                    str(image_data["name"]),
                    self._project.name,
                )

            if (
                self._project.project_type == constances.ProjectType.PIXEL.value
                and self._mask
            ):
                with open(self._mask, "rb") as fin:
                    file = io.BytesIO(fin.read())
                bucket.put_object(
                    Key=auth_data["images"][str(image_data["id"])][
                        "annotation_bluemap_path"
                    ],
                    Body=file,
                )
        return self._response


class UploadAnnotationsUseCase(BaseUseCase):
    MAX_WORKERS = 10

    def __init__(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        annotation_classes: List[AnnotationClassEntity],
        folder_path: str,
        annotation_paths: List[str],
        backend_service_provider: SuerannotateServiceProvider,
        templates: List[dict],
        pre_annotation: bool = False,
        client_s3_bucket=None,
    ):
        super().__init__()
        self._project = project
        self._folder = folder
        self._backend_service = backend_service_provider
        self._annotation_classes = annotation_classes
        self._folder_path = folder_path
        self._annotation_paths = annotation_paths
        self._client_s3_bucket = client_s3_bucket
        self._pre_annotation = pre_annotation
        self._templates = templates

    @property
    def s3_client(self):
        return boto3.client("s3")

    @property
    def annotation_classes_name_map(self) -> dict:
        classes_data = defaultdict(dict)
        annotation_classes = self._annotation_classes
        for annotation_class in annotation_classes:
            class_info = {"id": annotation_class.uuid}
            if annotation_class.attribute_groups:
                for attribute_group in annotation_class.attribute_groups:
                    attribute_group_data = defaultdict(dict)
                    for attribute in attribute_group["attributes"]:
                        attribute_group_data[attribute["name"]] = attribute["id"]
                    class_info["attribute_groups"] = {
                        attribute_group["name"]: {
                            "id": attribute_group["id"],
                            "attributes": attribute_group_data,
                        }
                    }
            classes_data[annotation_class.name] = class_info
        return classes_data

    @property
    def annotation_postfix(self):
        return (
            constances.VECTOR_ANNOTATION_POSTFIX
            if self._project.project_type == constances.ProjectType.VECTOR.value
            else constances.PIXEL_ANNOTATION_POSTFIX
        )

    def get_templates_mapping(self):
        templates_map = {}
        for template in self._templates:
            templates_map[template["name"]] = template["id"]
        return templates_map

    def fill_classes_data(self, annotations: dict):
        annotation_classes = self.annotation_classes_name_map
        if "instances" not in annotations:
            return
        unknown_classes = {}
        for annotation in [i for i in annotations["instances"] if "className" in i]:
            if "className" not in annotation:
                return
            annotation_class_name = annotation["className"]
            if annotation_class_name not in annotation_classes:
                if annotation_class_name not in unknown_classes:
                    unknown_classes[annotation_class_name] = {
                        "id": -(len(unknown_classes) + 1),
                        "attribute_groups": {},
                    }
        annotation_classes.update(unknown_classes)
        templates = self.get_templates_mapping()
        for annotation in (
            i for i in annotations["instances"] if i.get("type", None) == "template"
        ):
            annotation["templateId"] = templates.get(
                annotation.get("templateName", ""), -1
            )

        for annotation in [i for i in annotations["instances"] if "className" in i]:
            annotation_class_name = annotation["className"]
            if annotation_class_name not in annotation_classes:
                continue
            annotation["classId"] = annotation_classes[annotation_class_name]["id"]
            for attribute in annotation["attributes"]:
                if (
                    attribute["groupName"]
                    not in annotation_classes[annotation_class_name]["attribute_groups"]
                ):
                    continue
                attribute["groupId"] = annotation_classes[annotation_class_name][
                    "attribute_groups"
                ][attribute["groupName"]]["id"]
                if (
                    attribute["name"]
                    not in annotation_classes[annotation_class_name][
                        "attribute_groups"
                    ][attribute["groupName"]]["attributes"]
                ):
                    del attribute["groupId"]
                    continue
                attribute["id"] = annotation_classes[annotation_class_name][
                    "attribute_groups"
                ][attribute["groupName"]]["attributes"]

    def execute(self):
        annotation_paths = self._annotation_paths
        ImageInfo = namedtuple("ImageInfo", ["path", "name", "id"])
        images_detail = []
        for annotation_path in annotation_paths:
            images_detail.append(
                ImageInfo(
                    id=None,
                    path=annotation_path,
                    name=os.path.basename(
                        annotation_path.replace(
                            constances.PIXEL_ANNOTATION_POSTFIX, ""
                        ).replace(constances.VECTOR_ANNOTATION_POSTFIX, ""),
                    ),
                )
            )
        images_data = self._backend_service.get_bulk_images(
            images=[image.name for image in images_detail],
            folder_id=self._folder.uuid,
            team_id=self._project.team_id,
            project_id=self._project.uuid,
        )
        for image_data in images_data:
            for idx, detail in enumerate(images_detail):
                if detail.name == image_data.get("name"):
                    images_detail[idx] = detail._replace(id=image_data["id"])

        missing_annotations = list(
            filter(lambda detail: detail.id is None, images_detail)
        )
        annotations_to_upload = list(
            filter(lambda detail: detail.id is not None, images_detail)
        )
        if missing_annotations:
            for missing in missing_annotations:
                logger.warning(
                    f"Couldn't find image {missing.path} for annotation upload."
                )

        if self._pre_annotation:
            auth_data = self._backend_service.get_pre_annotation_upload_data(
                project_id=self._project.uuid,
                team_id=self._project.team_id,
                folder_id=self._folder.uuid,
                image_ids=[int(image.id) for image in annotations_to_upload],
            )
        else:
            auth_data = self._backend_service.get_annotation_upload_data(
                project_id=self._project.uuid,
                team_id=self._project.team_id,
                folder_id=self._folder.uuid,
                image_ids=[int(image.id) for image in annotations_to_upload],
            )
        session = boto3.Session(
            aws_access_key_id=auth_data["creds"]["accessKeyId"],
            aws_secret_access_key=auth_data["creds"]["secretAccessKey"],
            aws_session_token=auth_data["creds"]["sessionToken"],
            region_name=auth_data["creds"]["region"],
        )
        resource = session.resource("s3")
        bucket = resource.Bucket(auth_data["creds"]["bucket"])
        image_id_name_map = {str(image.id): image for image in annotations_to_upload}
        if self._client_s3_bucket:
            from_session = boto3.Session()
            from_s3 = from_session.resource("s3")
        else:
            from_s3 = None

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.MAX_WORKERS
        ) as executor:
            for image_id, image_info in auth_data["images"].items():
                executor.submit(
                    self.upload_to_s3,
                    image_id,
                    image_info,
                    bucket,
                    from_s3,
                    image_id_name_map,
                )

        uploaded_annotations = [annotation.path for annotation in annotations_to_upload]
        missing_annotations = [annotation.path for annotation in missing_annotations]
        failed_annotations = [
            annotation
            for annotation in annotation_paths
            if annotation not in uploaded_annotations + missing_annotations
        ]
        self._response.data = (
            uploaded_annotations,
            missing_annotations,
            failed_annotations,
        )
        return self._response

    def upload_to_s3(
        self, image_id: int, image_info, bucket, from_s3, image_id_name_map
    ):
        if from_s3:
            file = io.BytesIO()
            s3_object = from_s3.Object(
                self._client_s3_bucket, image_id_name_map[image_id].path
            )
            s3_object.download_fileobj(file)
            file.seek(0)
            annotation_json = json.load(file)
        else:
            annotation_json = json.load(open(image_id_name_map[image_id].path))

        self.fill_classes_data(annotation_json)
        bucket.put_object(
            Key=image_info["annotation_json_path"], Body=json.dumps(annotation_json),
        )
        if self._project.project_type == constances.ProjectType.PIXEL.value:
            mask_filename = (
                image_id_name_map[image_id].name + constances.ANNOTATION_MASK_POSTFIX
            )
            if from_s3:
                file = io.BytesIO()
                s3_object = self._client_s3_bucket.Objcect(
                    self._client_s3_bucket, self._folder_path + mask_filename
                )
                s3_object.download_file(file)
                file.seek(0)
            else:
                with open(f"{self._folder_path}/{mask_filename}", "rb") as mask_file:
                    file = io.BytesIO(mask_file.read())

            bucket.put_object(Key=image_info["annotation_bluemap_path"], Body=file)


class CreateModelUseCase(BaseUseCase):
    def __init__(
        self,
        base_model_name: str,
        model_name: str,
        model_description: str,
        task: str,
        team_id: int,
        train_data_paths: Iterable[str],
        test_data_paths: Iterable[str],
        backend_service_provider: SuerannotateServiceProvider,
        projects: BaseReadOnlyRepository,
        folders: BaseReadOnlyRepository,
        ml_models: BaseManageableRepository,
        hyper_parameters: dict = None,
    ):
        super().__init__()
        self._base_model_name = base_model_name
        self._model_name = model_name
        self._model_description = model_description
        self._task = task
        self._team_id = team_id
        self._hyper_parameters = hyper_parameters
        self._train_data_paths = train_data_paths
        self._test_data_paths = test_data_paths
        self._backend_service = backend_service_provider
        self._ml_models = ml_models
        self._projects = projects
        self._folders = folders

    @property
    def hyper_parameters(self):
        if self._hyper_parameters:
            for parameter in constances.DEFAULT_HYPER_PARAMETERS:
                if parameter not in self._hyper_parameters:
                    self._hyper_parameters[
                        parameter
                    ] = constances.DEFAULT_HYPER_PARAMETERS[parameter]
        else:
            self._hyper_parameters = constances.DEFAULT_HYPER_PARAMETERS
        return self._hyper_parameters

    @staticmethod
    def split_path(path: str):
        if "/" in path:
            return path.split("/")
        return path, "root"

    def execute(self):
        train_folder_ids = []
        test_folder_ids = []
        projects = []

        for path in self._train_data_paths:
            project_name, folder_name = self.split_path(path)
            projects = self._projects.get_all(
                Condition("name", project_name, EQ)
                & Condition("team_id", self._team_id, EQ)
            )

            projects.extend(projects)
            folders = self._folders.get_all(
                Condition("name", folder_name, EQ)
                & Condition("team_id", self._team_id, EQ)
                & Condition("project_id", projects[0].uuid, EQ)
            )
            train_folder_ids.append(folders[0].uuid)

        for path in self._test_data_paths:
            project_name, folder_name = self.split_path(path)
            projects.extend(
                self._projects.get_all(
                    Condition("name", project_name, EQ)
                    & Condition("team_id", self._team_id, EQ)
                )
            )
            folders = self._folders.get_all(
                Condition("name", folder_name, EQ)
                & Condition("team_id", self._team_id, EQ)
                & Condition("project_id", projects[0].uuid, EQ)
            )
            test_folder_ids.append(folders[0].uuid)

        project_types = [project.project_type for project in projects]

        if set(train_folder_ids) & set(test_folder_ids):
            self._response.errors = AppException(
                "Avoid overlapping between training and test data."
            )
            return
        if len(set(project_types)) != 1:
            self._response.errors = AppException(
                "All projects have to be of the same type. Either vector or pixel"
            )
            return
        if any(
            {
                True
                for project in projects
                if project.upload_state == constances.UploadState.EXTERNAL.value
            }
        ):
            self._response.errors = AppException(
                "The function does not support projects containing images attached with URLs"
            )
            return

        base_model = self._ml_models.get_all(
            Condition("name", self._base_model_name, EQ)
            & Condition("team_id", self._team_id, EQ)
            & Condition("task", constances.MODEL_TRAINING_TASKS[self._task], EQ)
            & Condition("type", project_types[0], EQ)
            & Condition("include_global", True, EQ)
        )[0]

        if base_model.model_type != project_types[0]:
            self._response.errors = AppException(
                f"The type of provided projects is {project_types[0]}, "
                "and does not correspond to the type of provided model"
            )
            return self._response

        completed_images_data = self._backend_service.bulk_get_folders(
            self._team_id, [project.uuid for project in projects]
        )
        complete_image_count = sum(
            [
                folder["completedCount"]
                for folder in completed_images_data["data"]
                if folder["id"] in train_folder_ids
            ]
        )
        ml_model = MLModelEntity(
            name=self._model_name,
            description=self._model_description,
            task=constances.MODEL_TRAINING_TASKS[self._task],
            base_model_id=base_model.uuid,
            image_count=complete_image_count,
            model_type=project_types[0],
            train_folder_ids=train_folder_ids,
            test_folder_ids=test_folder_ids,
            hyper_parameters=self.hyper_parameters,
        )
        new_model_data = self._ml_models.insert(ml_model)

        self._response.data = new_model_data
        return self._response


class GetModelMetricsUseCase(BaseUseCase):
    def __init__(
        self,
        model_id: int,
        team_id: int,
        backend_service_provider: SuerannotateServiceProvider,
    ):
        super().__init__()
        self._model_id = model_id
        self._team_id = team_id
        self._backend_service = backend_service_provider

    def execute(self):
        metrics = self._backend_service.get_model_metrics(
            team_id=self._team_id, model_id=self._model_id
        )
        self._response.data = metrics
        return self._response


class UpdateModelUseCase(BaseUseCase):
    def __init__(
        self, model: MLModelEntity, models: BaseManageableRepository,
    ):
        super().__init__()
        self._models = models
        self._model = model

    def execute(self):
        model = self._models.update(self._model)
        self._response.data = model
        return self._response


class DeleteMLModel(BaseUseCase):
    def __init__(self, model_id: int, models: BaseManageableRepository):
        super().__init__()
        self._model_id = model_id
        self._models = models

    def execute(self):
        self._response.data = self._models.delete(self._model_id)
        return self._response


class StopModelTraining(BaseUseCase):
    def __init__(
        self,
        model_id: int,
        team_id: int,
        backend_service_provider: SuerannotateServiceProvider,
    ):
        super().__init__()

        self._model_id = model_id
        self._team_id = team_id
        self._backend_service = backend_service_provider

    def execute(self):
        is_stopped = self._backend_service.stop_model_training(
            self._team_id, self._model_id
        )
        if not is_stopped:
            self._response.errors = AppException("Something went wrong.")
        return self._response


class DownloadExportUseCase(BaseUseCase):
    def __init__(
        self,
        service: SuerannotateServiceProvider,
        project: ProjectEntity,
        export_name: str,
        folder_path: str,
        extract_zip_contents: bool,
        to_s3_bucket: bool,
    ):
        super().__init__()
        self._service = service
        self._project = project
        self._export_name = export_name
        self._folder_path = folder_path
        self._extract_zip_contents = extract_zip_contents
        self._to_s3_bucket = to_s3_bucket

    def execute(self):
        exports = self._service.get_exports(
            team_id=self._project.team_id, project_id=self._project.uuid
        )
        export_id = None
        for export in exports:
            if export["name"] == self._export_name:
                export_id = export["id"]
                break
        if not export_id:
            raise AppException("Export not found.")

        while True:
            export = self._service.get_export(
                team_id=self._project.team_id,
                project_id=self._project.uuid,
                export_id=export_id,
            )

            if export["status"] == ExportStatus.IN_PROGRESS.value:
                logger.info("Waiting 5 seconds for export to finish on server.")
                time.sleep(5)
                continue
            if export["status"] == ExportStatus.ERROR.value:
                raise AppException("Couldn't download export.")
                pass
            break

        filename = Path(export["path"]).name
        filepath = Path(self._folder_path) / filename
        with requests.get(export["download"], stream=True) as r:
            r.raise_for_status()
            with open(filepath, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        if self._extract_zip_contents:
            with zipfile.ZipFile(filepath, "r") as f:
                f.extractall(self._folder_path)
            Path.unlink(filepath)
            logger.info(f"Extracted {filepath} to folder {self._folder_path}")
        else:
            logger.info(f"Downloaded export ID {export['id']} to {filepath}")

        self._response.data = self._folder_path
        return self._response


class DownloadMLModelUseCase(BaseUseCase):
    def __init__(
        self,
        model: MLModelEntity,
        download_path: str,
        backend_service_provider: SuerannotateServiceProvider,
        team_id: int,
    ):
        super().__init__()
        self._model = model
        self._download_path = download_path
        self._backend_service = backend_service_provider
        self._team_id = team_id

    def execute(self):
        metrics_name = os.path.basename(self._model.path).replace(".pth", ".json")
        mapper_path = self._model.config_path.replace(
            os.path.basename(self._model.config_path), "classes_mapper.json"
        )
        metrics_path = self._model.config_path.replace(
            os.path.basename(self._model.config_path), metrics_name
        )

        download_token = self._backend_service.get_ml_model_download_tokens(
            self._team_id, self._model.uuid
        )
        s3_session = boto3.Session(
            aws_access_key_id=download_token["tokens"]["accessKeyId"],
            aws_secret_access_key=download_token["tokens"]["secretAccessKey"],
            aws_session_token=download_token["tokens"]["sessionToken"],
            region_name=download_token["tokens"]["region"],
        )
        bucket = s3_session.resource("s3").Bucket(download_token["tokens"]["bucket"])

        bucket.download_file(
            self._model.config_path, os.path.join(self._download_path, "config.yaml")
        )
        bucket.download_file(
            self._model.path,
            os.path.join(self._download_path, os.path.basename(self._model.path)),
        )
        if self._model.is_global:
            try:
                bucket.download_file(
                    metrics_path, os.path.join(self._download_path, metrics_name)
                )
                bucket.download_file(
                    mapper_path,
                    os.path.join(self._download_path, "classes_mapper.json"),
                )
            except Boto3Error:
                self._response.errors = AppException(
                    "The specified model does not contain a classes_mapper and/or a metrics file."
                )
        self._response.data = self._model
        return self._response


class BenchmarkUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        ground_truth_folder_name: str,
        folder_names: list,
        export_dir: str,
        image_list: list,
        annotation_type: str,
        show_plots: bool,
    ):
        super().__init__()
        self._project = project
        self._ground_truth_folder_name = ground_truth_folder_name
        self._folder_names = folder_names
        self._export_dir = export_dir
        self._image_list = image_list
        self._annotation_type = annotation_type
        self._show_plots = show_plots

    def execute(self):
        project_df = aggregate_annotations_as_df(self._export_dir)
        gt_project_df = project_df[
            project_df["folderName"] == self._ground_truth_folder_name
        ]
        benchmark_dfs = []
        for folder_name in self._folder_names:
            folder_df = project_df[project_df["folderName"] == folder_name]
            project_gt_df = pd.concat([folder_df, gt_project_df])
            project_gt_df = project_gt_df[project_gt_df["instanceId"].notna()]

            if self._image_list is not None:
                project_gt_df = project_gt_df.loc[
                    project_gt_df["imageName"].isin(self._image_list)
                ]

            project_gt_df.query("type == '" + self._annotation_type + "'", inplace=True)

            project_gt_df = project_gt_df.groupby(
                ["imageName", "instanceId", "folderName"]
            )

            def aggregate_attributes(instance_df):
                def attribute_to_list(attribute_df):
                    attribute_names = list(attribute_df["attributeName"])
                    attribute_df["attributeNames"] = len(attribute_df) * [
                        attribute_names
                    ]
                    return attribute_df

                attributes = None
                if not instance_df["attributeGroupName"].isna().all():
                    attrib_group_name = instance_df.groupby("attributeGroupName")[
                        ["attributeGroupName", "attributeName"]
                    ].apply(attribute_to_list)
                    attributes = dict(
                        zip(
                            attrib_group_name["attributeGroupName"],
                            attrib_group_name["attributeNames"],
                        )
                    )

                instance_df.drop(
                    ["attributeGroupName", "attributeName"], axis=1, inplace=True
                )
                instance_df.drop_duplicates(
                    subset=["imageName", "instanceId", "folderName"], inplace=True
                )
                instance_df["attributes"] = [attributes]
                return instance_df

            project_gt_df = project_gt_df.apply(aggregate_attributes).reset_index(
                drop=True
            )
            unique_images = set(project_gt_df["imageName"])
            all_benchmark_data = []
            for image_name in unique_images:
                image_data = image_consensus(
                    project_gt_df, image_name, self._annotation_type
                )
                all_benchmark_data.append(pd.DataFrame(image_data))
            benchmark_project_df = pd.concat(all_benchmark_data, ignore_index=True)
            benchmark_project_df = benchmark_project_df[
                benchmark_project_df["folderName"] == folder_name
            ]
            benchmark_dfs.append(benchmark_project_df)
        benchmark_df = pd.concat(benchmark_dfs, ignore_index=True)
        if self._show_plots:
            consensus_plot(benchmark_df, self._folder_names)
        self._response.data = benchmark_df
        return self._response


class ConsensusUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        folder_names: list,
        export_dir: str,
        image_list: list,
        annotation_type: str,
        show_plots: bool,
    ):
        super().__init__()
        self._project = project
        self._folder_names = folder_names
        self._export_dir = export_dir
        self._image_list = image_list
        self._annota_type_type = annotation_type
        self._show_plots = show_plots

    def execute(self):
        project_df = aggregate_annotations_as_df(self._export_dir)
        all_projects_df = project_df[project_df["instanceId"].notna()]
        all_projects_df = all_projects_df.loc[
            all_projects_df["folderName"].isin(self._folder_names)
        ]

        if self._image_list is not None:
            all_projects_df = all_projects_df.loc[
                all_projects_df["imageName"].isin(self._image_list)
            ]

        all_projects_df.query("type == '" + self._annota_type_type + "'", inplace=True)

        def aggregate_attributes(instance_df):
            def attribute_to_list(attribute_df):
                attribute_names = list(attribute_df["attributeName"])
                attribute_df["attributeNames"] = len(attribute_df) * [attribute_names]
                return attribute_df

            attributes = None
            if not instance_df["attributeGroupName"].isna().all():
                attrib_group_name = instance_df.groupby("attributeGroupName")[
                    ["attributeGroupName", "attributeName"]
                ].apply(attribute_to_list)
                attributes = dict(
                    zip(
                        attrib_group_name["attributeGroupName"],
                        attrib_group_name["attributeNames"],
                    )
                )

            instance_df.drop(
                ["attributeGroupName", "attributeName"], axis=1, inplace=True
            )
            instance_df.drop_duplicates(
                subset=["imageName", "instanceId", "folderName"], inplace=True
            )
            instance_df["attributes"] = [attributes]
            return instance_df

        all_projects_df = all_projects_df.groupby(
            ["imageName", "instanceId", "folderName"]
        )
        all_projects_df = all_projects_df.apply(aggregate_attributes).reset_index(
            drop=True
        )
        unique_images = set(all_projects_df["imageName"])
        all_consensus_data = []
        for image_name in unique_images:
            image_data = image_consensus(
                all_projects_df, image_name, self._annota_type_type
            )
            all_consensus_data.append(pd.DataFrame(image_data))

        consensus_df = pd.concat(all_consensus_data, ignore_index=True)

        if self._show_plots:
            consensus_plot(consensus_df, self._folder_names)

        self._response.data = consensus_df
        return self._response


class RunSegmentationUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        ml_model_repo: BaseManageableRepository,
        ml_model_name: str,
        images_list: list,
        service: SuerannotateServiceProvider,
        folder: FolderEntity,
    ):
        super().__init__()
        self._project = project
        self._ml_model_repo = ml_model_repo
        self._ml_model_name = ml_model_name
        self._images_list = images_list
        self._service = service
        self._folder = folder

    def validate_project_type(self):
        if self._project.project_type is not ProjectType.PIXEL.value:
            raise AppValidationException(
                "Operation not supported for given project type"
            )

    def validate_model(self):
        if self._ml_model_name not in constances.AVAILABLE_SEGMENTATION_MODELS:
            raise AppValidationException("Model Does not exist")

    def validate_upload_state(self):

        if self._project.upload_state is constances.UploadState.EXTERNAL:
            raise AppValidationException(
                "The function does not support projects containing images attached with URLs"
            )

    def execute(self):
        if self.is_valid():
            images = (
                GetBulkImages(
                    service=self._service,
                    project_id=self._project.uuid,
                    team_id=self._project.team_id,
                    folder_id=self._folder.uuid,
                    images=self._images_list,
                )
                .execute()
                .data
            )

            image_ids = [image.uuid for image in images]
            image_names = [image.name for image in images]

            if not len(image_names):
                self._response.errors = AppException(
                    "No valid image names were provided."
                )
                return self._response

            res = self._service.run_segmentation(
                self._project.team_id,
                self._project.uuid,
                model_name=self._ml_model_name,
                image_ids=image_ids,
            )
            if not res.ok:
                return self._response

            success_images = []
            failed_images = []
            while len(success_images) + len(failed_images) != len(image_ids):
                images_metadata = (
                    GetBulkImages(
                        service=self._service,
                        project_id=self._project.uuid,
                        team_id=self._project.team_id,
                        folder_id=self._folder.uuid,
                        images=self._images_list,
                    )
                    .execute()
                    .data
                )

                success_images = [
                    img.name
                    for img in images_metadata
                    if img.segmentation_status
                    == constances.SegmentationStatus.COMPLETED.value
                ]
                failed_images = [
                    img.name
                    for img in images_metadata
                    if img.segmentation_status
                    == constances.SegmentationStatus.FAILED.value
                ]
                logger.info(
                    f"segmentation complete on {len(success_images + failed_images)} / {len(image_ids)} images"
                )
                time.sleep(5)

            self._response.data = (success_images, failed_images)
        return self._response


class RunPredictionUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        ml_model_repo: BaseManageableRepository,
        ml_model_name: str,
        images_list: list,
        service: SuerannotateServiceProvider,
        folder: FolderEntity,
    ):
        super().__init__()
        self._project = project
        self._ml_model_repo = ml_model_repo
        self._ml_model_name = ml_model_name
        self._images_list = images_list
        self._service = service
        self._folder = folder

    def execute(self):
        if self.is_valid():
            images = (
                GetBulkImages(
                    service=self._service,
                    project_id=self._project.uuid,
                    team_id=self._project.team_id,
                    folder_id=self._folder.uuid,
                    images=self._images_list,
                )
                .execute()
                .data
            )

            image_ids = [image.uuid for image in images]
            image_names = [image.name for image in images]

            if not len(image_names):
                self._response.errors = AppException(
                    "No valid image names were provided."
                )
                return self._response

            ml_models = self._ml_model_repo.get_all(
                condition=Condition("name", self._ml_model_name, EQ)
                & Condition("include_global", True, EQ)
                & Condition("team_id", self._project.team_id, EQ)
            )
            ml_model = None
            for model in ml_models:
                if model.name == self._ml_model_name:
                    ml_model = model

            res = self._service.run_prediction(
                team_id=self._project.team_id,
                project_id=self._project.uuid,
                ml_model_id=ml_model.uuid,
                image_ids=image_ids,
            )
            if not res.ok:
                return self._response

            success_images = []
            failed_images = []
            while len(success_images) + len(failed_images) != len(image_ids):
                images_metadata = (
                    GetBulkImages(
                        service=self._service,
                        project_id=self._project.uuid,
                        team_id=self._project.team_id,
                        folder_id=self._folder.uuid,
                        images=self._images_list,
                    )
                    .execute()
                    .data
                )

                success_images = [
                    img.name
                    for img in images_metadata
                    if img.segmentation_status
                    == constances.SegmentationStatus.COMPLETED.value
                ]
                failed_images = [
                    img.name
                    for img in images_metadata
                    if img.segmentation_status
                    == constances.SegmentationStatus.FAILED.value
                ]

                complete_images = success_images + failed_images
                logger.info(
                    f"prediction complete on {len(complete_images)} / {len(image_ids)} images"
                )
                time.sleep(5)

            self._response.data = (success_images, failed_images)
        return self._response


class GetAllImagesUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        service_provider: SuerannotateServiceProvider,
        annotation_status: str = None,
        name_prefix: str = None,
    ):
        super().__init__()
        self._project = project
        self._service_provider = service_provider
        self._annotation_status = annotation_status
        self._name_prefix = name_prefix

    @property
    def annotation_status(self):
        return constances.AnnotationStatus.get_value(self._annotation_status)

    def execute(self):
        condition = (
            Condition("team_id", self._project.team_id, EQ)
            & Condition("project_id", self._project.uuid, EQ)
            & Condition("folder_id", 0, EQ)
        )
        if self._annotation_status:
            condition &= Condition("annotation_status", self.annotation_status, EQ)
        if self._name_prefix:
            condition &= Condition("name", self._name_prefix, EQ)
        self._response.data = self._service_provider.list_images(
            query_string=condition.build_query()
        )
        return self._response


class SearchMLModels(BaseUseCase):
    def __init__(
        self, ml_models_repo: BaseManageableRepository, condition: Condition,
    ):
        super().__init__()
        self._ml_models = ml_models_repo
        self._condition = condition

    def execute(self):
        ml_models = self._ml_models.get_all(condition=self._condition)
        ml_models = [ml_model.to_dict() for ml_model in ml_models]
        self._response.data = ml_models
        return self._response


class UploadFileToS3UseCase(BaseUseCase):
    def __init__(self, to_s3_bucket, path, s3_key: str):
        super().__init__()
        self._to_s3_bucket = to_s3_bucket
        self._path = path
        self._s3_key = s3_key

    def execute(self):
        self._to_s3_bucket.upload_file(str(self._path), self._s3_key)


class UploadImagesFromFolderToProject(BaseInteractiveUseCase):
    MAX_WORKERS = 10

    def __init__(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        settings: BaseManageableRepository,
        s3_repo,
        backend_client: SuerannotateServiceProvider,
        folder_path: str,
        extensions=constances.DEFAULT_IMAGE_EXTENSIONS,
        annotation_status="NotStarted",
        from_s3_bucket=None,
        exclude_file_patterns: List[str] = constances.DEFAULT_FILE_EXCLUDE_PATTERNS,
        recursive_sub_folders: bool = False,
        image_quality_in_editor=None,
    ):
        super().__init__()

        self._auth_data = None
        self._s3_repo_instance = None
        self._images_to_upload = None

        self._project = project
        self._folder = folder
        self._folder_path = folder_path
        self._settings = settings.get_all()
        self._s3_repo = s3_repo
        self._backend_client = backend_client
        self._image_quality_in_editor = image_quality_in_editor
        self._from_s3_bucket = from_s3_bucket
        self._extensions = extensions
        self._recursive_sub_folders = recursive_sub_folders
        if exclude_file_patterns:
            list(exclude_file_patterns).extend(
                list(constances.DEFAULT_FILE_EXCLUDE_PATTERNS)
            )
        self._exclude_file_patterns = exclude_file_patterns
        self._annotation_status = annotation_status

    @property
    def extensions(self):
        if not self._extensions:
            return constances.DEFAULT_IMAGE_EXTENSIONS
        return self._extensions

    @property
    def exclude_file_patterns(self):
        if not self._exclude_file_patterns:
            return constances.DEFAULT_FILE_EXCLUDE_PATTERNS
        return self._exclude_file_patterns

    def validate_annotation_status(self):
        if (
            self._annotation_status
            and self._annotation_status.lower()
            not in constances.AnnotationStatus.values()
        ):
            raise AppValidationException("Invalid annotations status")

    def validate_extensions(self):
        if self._extensions and not all(
            [
                extension in constances.DEFAULT_IMAGE_EXTENSIONS
                for extension in self._extensions
            ]
        ):
            raise AppValidationException("")

    def validate_project_type(self):
        if self._project.project_type == constances.ProjectType.VIDEO.value:
            raise AppValidationException(
                "The function does not support projects containing videos attached with URLs"
            )

    def validate_auth_data(self):
        response = self._backend_client.get_s3_upload_auth_token(
            team_id=self._project.team_id,
            folder_id=self._folder.uuid,
            project_id=self._project.uuid,
        )
        if "error" in response:
            raise AppException(response.get("error"))
        self._auth_data = response

    @property
    def auth_data(self):
        return self._auth_data

    @property
    def s3_repository(self):
        if not self._s3_repo_instance:
            self._s3_repo_instance = self._s3_repo(
                self.auth_data["accessKeyId"],
                self.auth_data["secretAccessKey"],
                self.auth_data["sessionToken"],
                self.auth_data["bucket"],
            )
        return self._s3_repo_instance

    def _upload_image(self, image_path: str):
        ProcessedImage = namedtuple(
            "ProcessedImage", ["uploaded", "path", "entity", "name"]
        )
        if self._from_s3_bucket:
            image_bytes = (
                GetS3ImageUseCase(s3_bucket=self._from_s3_bucket, image_path=image_path)
                .execute()
                .data
            )
        else:
            image_bytes = io.BytesIO(open(image_path, "rb").read())
        upload_response = UploadImageS3UseCase(
            project=self._project,
            project_settings=self._settings,
            image_path=image_path,
            image=image_bytes,
            s3_repo=self.s3_repository,
            upload_path=self.auth_data["filePath"],
            image_quality_in_editor=self._image_quality_in_editor,
        ).execute()

        if not upload_response.errors and upload_response.data:
            entity = upload_response.data
            return ProcessedImage(
                uploaded=True,
                path=entity.path,
                entity=entity,
                name=Path(image_path).name,
            )
        else:
            return ProcessedImage(
                uploaded=False, path=image_path, entity=None, name=Path(image_path).name
            )

    @property
    def paths(self):
        paths = []
        if self._from_s3_bucket is None:
            for extension in self.extensions:
                if self._recursive_sub_folders:
                    paths += list(
                        Path(self._folder_path).rglob(f"*.{extension.lower()}")
                    )
                    if os.name != "nt":
                        paths += list(
                            Path(self._folder_path).rglob(f"*.{extension.upper()}")
                        )
                else:
                    paths += list(
                        Path(self._folder_path).glob(f"*.{extension.lower()}")
                    )
                    if os.name != "nt":
                        paths += list(
                            Path(self._folder_path).glob(f"*.{extension.upper()}")
                        )

        else:
            s3_client = boto3.client("s3")
            paginator = s3_client.get_paginator("list_objects_v2")
            response_iterator = paginator.paginate(
                Bucket=self._from_s3_bucket, Prefix=self._folder_path
            )
            for response in response_iterator:
                for object_data in response["Contents"]:
                    key = object_data["Key"]
                    if (
                        not self._recursive_sub_folders
                        and "/" in key[len(self._folder_path) + 1 :]
                    ):
                        continue
                    for extension in self._extensions:
                        if key.endswith(f".{extension.lower()}") or key.endswith(
                            f".{extension.upper()}"
                        ):
                            paths.append(key)
                            break

        data = []
        for path in paths:
            if all(
                [
                    True if exclude_pattern not in str(path) else False
                    for exclude_pattern in self.exclude_file_patterns
                ]
            ):
                data.append(str(path))
        return data

    @property
    def images_to_upload(self):
        if not self._images_to_upload:
            paths = self.paths
            filtered_paths = []
            duplicated_paths = []
            images = self._backend_client.get_bulk_images(
                project_id=self._project.uuid,
                team_id=self._project.team_id,
                folder_id=self._folder.uuid,
                images=[Path(image).name for image in paths],
            )
            image_entities = (
                GetBulkImages(
                    service=self._backend_client,
                    project_id=self._project.uuid,
                    team_id=self._project.team_id,
                    folder_id=self._folder.uuid,
                    images=[Path(image).name for image in paths],
                )
                .execute()
                .data
            )

            for path in paths:
                not_in_exclude_list = [
                    x not in Path(path).name for x in self.exclude_file_patterns
                ]
                non_in_service_list = [
                    x.name not in Path(path).name for x in image_entities
                ]
                if (
                    all(not_in_exclude_list)
                    and all(non_in_service_list)
                    and not any(
                        Path(path).name in filtered_path
                        for filtered_path in filtered_paths
                    )
                ):
                    filtered_paths.append(path)
                elif not all(non_in_service_list) or any(
                    Path(path).name in filtered_path for filtered_path in filtered_paths
                ):
                    duplicated_paths.append(path)

            self._images_to_upload = list(set(filtered_paths)), duplicated_paths
        return self._images_to_upload

    def execute(self):
        if self.is_valid():
            images_to_upload, duplications = self.images_to_upload
            images_to_upload = images_to_upload[: self.auth_data["availableImageCount"]]
            uploaded_images = []
            failed_images = []
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=self.MAX_WORKERS
            ) as executor:
                results = [
                    executor.submit(self._upload_image, image_path)
                    for image_path in images_to_upload
                ]
                for future in concurrent.futures.as_completed(results):
                    processed_image = future.result()
                    if processed_image.uploaded and processed_image.entity:
                        uploaded_images.append(processed_image)
                    else:
                        failed_images.append(processed_image.path)
                    yield

            uploaded = []
            for i in range(0, len(uploaded_images), 100):
                response = AttachFileUrlsUseCase(
                    project=self._project,
                    folder=self._folder,
                    limit=self.auth_data["availableImageCount"],
                    backend_service_provider=self._backend_client,
                    attachments=[
                        image.entity for image in uploaded_images[i : i + 100]
                    ],
                    annotation_status=self._annotation_status,
                ).execute()
                if response.errors:
                    logger.error(response.errors)
                    continue
                attachments, attach_duplications = response.data
                uploaded.extend(attachments)
                duplications.extend(attach_duplications)
            uploaded = [image["name"] for image in uploaded]
            failed_images = [image.split("/")[-1] for image in failed_images]

            self._response.data = uploaded, failed_images, duplications
        return self._response


class DeleteAnnotations(BaseUseCase):
    POLL_AWAIT_TIME = 2
    CHUNK_SIZE = 2000

    def __init__(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        backend_service: SuerannotateServiceProvider,
        image_names: Optional[List[str]] = None,
    ):
        super().__init__()
        self._project = project
        self._folder = folder
        self._image_names = image_names
        self._backend_service = backend_service

    def execute(self) -> Response:
        polling_states = {}
        if self._image_names:
            for idx in range(0, len(self._image_names), self.CHUNK_SIZE):
                response = self._backend_service.delete_image_annotations(
                    project_id=self._project.uuid,
                    team_id=self._project.team_id,
                    folder_id=self._folder.uuid,
                    image_names=self._image_names[
                        idx : idx + self.CHUNK_SIZE
                    ],  # noqa: E203
                )
                if response:
                    polling_states[response.get("poll_id")] = False
        else:
            response = self._backend_service.delete_image_annotations(
                project_id=self._project.uuid,
                team_id=self._project.team_id,
                folder_id=self._folder.uuid,
            )
            if response:
                polling_states[response.get("poll_id")] = False

        if not polling_states:
            self._response.errors = AppException("Invalid image names or empty folder.")
        else:
            for poll_id in polling_states:
                timeout_start = time.time()
                while time.time() < timeout_start + self.POLL_AWAIT_TIME:
                    progress = int(
                        self._backend_service.get_annotations_delete_progress(
                            project_id=self._project.uuid,
                            team_id=self._project.team_id,
                            poll_id=poll_id,
                        ).get("process", -1)
                    )
                    if 0 < progress < 100:
                        logger.info("Delete annotations in progress.")
                    elif 0 > progress:
                        polling_states[poll_id] = False
                        self._response.errors = "Annotations delete fails."
                        continue
                    else:
                        polling_states[poll_id] = True
                        continue

            project_folder_name = (
                self._project.name
                + (f"/{self._folder.name}" if self._folder.name != "root" else "")
                + "."
            )

            if all(polling_states.values()):
                logger.info(
                    "The annotations have been successfully deleted from "
                    + project_folder_name
                )
            else:
                logger.info("Annotations delete fails.")
        return self._response


class GetBulkImages(BaseUseCase):
    def __init__(
        self,
        service: SuerannotateServiceProvider,
        project_id: int,
        team_id: int,
        folder_id: int,
        images: List[str],
    ):
        super().__init__()
        self._service = service
        self._project_id = project_id
        self._team_id = team_id
        self._folder_id = folder_id
        self._images = images
        self._chunk_size = 500

    def execute(self):
        res = []
        for i in range(0, len(self._images), self._chunk_size):
            images = self._service.get_bulk_images(
                project_id=self._project_id,
                team_id=self._team_id,
                folder_id=self._folder_id,
                images=self._images[i : i + self._chunk_size],
            )
            res += [ImageEntity.from_dict(**image) for image in images]
        self._response.data = res
        return self._response
