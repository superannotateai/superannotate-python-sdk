import copy
from typing import List

import superannotate.lib.core as constances
from lib.core.conditions import Condition
from lib.core.conditions import CONDITION_EQ as EQ
from lib.core.entities import AttachmentEntity
from lib.core.entities import DocumentEntity
from lib.core.entities import Entity
from lib.core.entities import FolderEntity
from lib.core.entities import ProjectEntity
from lib.core.entities import TmpBaseEntity
from lib.core.entities import TmpImageEntity
from lib.core.entities import VideoEntity
from lib.core.exceptions import AppException
from lib.core.exceptions import AppValidationException
from lib.core.reporter import Reporter
from lib.core.repositories import BaseReadOnlyRepository
from lib.core.response import Response
from lib.core.serviceproviders import SuperannotateServiceProvider
from lib.core.usecases.base import BaseReportableUseCae
from pydantic import parse_obj_as


class GetItem(BaseReportableUseCae):
    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        folder: FolderEntity,
        items: BaseReadOnlyRepository,
        item_name: str,
    ):
        super().__init__(reporter)
        self._project = project
        self._folder = folder
        self._items = items
        self._item_name = item_name

    @staticmethod
    def serialize_entity(entity: Entity, project: ProjectEntity):
        if project.upload_state != constances.UploadState.EXTERNAL.value:
            entity.url = None
        if project.project_type in (
            constances.ProjectType.VECTOR.value,
            constances.ProjectType.PIXEL.value,
        ):
            tmp_entity = entity
            if project.project_type == constances.ProjectType.VECTOR.value:
                entity.segmentation_status = None
            if project.upload_state == constances.UploadState.EXTERNAL.value:
                tmp_entity.prediction_status = None
                tmp_entity.segmentation_status = None
            return TmpImageEntity(**tmp_entity.dict(by_alias=True))
        elif project.project_type == constances.ProjectType.VIDEO.value:
            return VideoEntity(**entity.dict(by_alias=True))
        elif project.project_type == constances.ProjectType.DOCUMENT.value:
            return DocumentEntity(**entity.dict(by_alias=True))
        return entity

    def execute(self) -> Response:
        if self.is_valid():
            condition = (
                Condition("name", self._item_name, EQ)
                & Condition("team_id", self._project.team_id, EQ)
                & Condition("project_id", self._project.uuid, EQ)
                & Condition("folder_id", self._folder.uuid, EQ)
            )
            entity = self._items.get_one(condition)
            if entity:
                entity.add_path(self._project.name, self._folder.name)
                self._response.data = self.serialize_entity(entity, self._project)
            else:
                self._response.errors = AppException("Item not found.")
        return self._response


class QueryEntities(BaseReportableUseCae):
    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        folder: FolderEntity,
        backend_service_provider: SuperannotateServiceProvider,
        query: str,
    ):
        super().__init__(reporter)
        self._project = project
        self._folder = folder
        self._backend_client = backend_service_provider
        self._query = query

    def validate_query(self):
        response = self._backend_client.validate_saqul_query(
            self._project.team_id, self._project.uuid, self._query
        )
        if response.get("error"):
            raise AppException(response["error"])
        if response["isValidQuery"]:
            self._query = response["parsedQuery"]
        else:
            raise AppException("Incorrect query.")
        if self._project.sync_status != constances.ProjectState.SYNCED.value:
            raise AppException("Data is not synced.")

    def execute(self) -> Response:
        if self.is_valid():
            service_response = self._backend_client.saqul_query(
                self._project.team_id,
                self._project.uuid,
                self._query,
                folder_id=None if self._folder.name == "root" else self._folder.uuid,
            )
            if service_response.ok:
                data = parse_obj_as(List[TmpBaseEntity], [Entity.map_fields(i) for i in service_response.data])
                for i, item in enumerate(data):
                    data[i] = GetItem.serialize_entity(item, self._project)
                self._response.data = data
            else:
                self._response.errors = service_response.data
        return self._response


class ListItems(BaseReportableUseCae):
    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        folder: FolderEntity,
        items: BaseReadOnlyRepository,
        search_condition: Condition,
        folders: BaseReadOnlyRepository,
        recursive: bool = False,
    ):
        super().__init__(reporter)
        self._project = project
        self._folder = folder
        self._items = items
        self._folders = folders
        self._search_condition = search_condition
        self._recursive = recursive

    def validate_recursive_case(self):
        if not self._folder.is_root and self._recursive:
            self._recursive = False

    def execute(self) -> Response:
        if self.is_valid():
            self._search_condition &= Condition("team_id", self._project.team_id, EQ)
            self._search_condition &= Condition("project_id", self._project.uuid, EQ)

            if not self._recursive:
                self._search_condition &= Condition("folder_id", self._folder.uuid, EQ)
                items = [
                    GetItem.serialize_entity(
                        item.add_path(self._project.name, self._folder.name),
                        self._project,
                    )
                    for item in self._items.get_all(self._search_condition)
                ]
            else:
                items = []
                folders = self._folders.get_all(
                    Condition("team_id", self._project.team_id, EQ)
                    & Condition("project_id", self._project.uuid, EQ),
                )
                folders.append(self._folder)
                for folder in folders:
                    tmp = self._items.get_all(
                        copy.deepcopy(self._search_condition) & Condition("folder_id", folder.uuid, EQ)
                    )
                    items.extend(
                        [
                            GetItem.serialize_entity(
                                item.add_path(self._project.name, folder.name),
                                self._project,
                            )
                            for item in tmp
                        ]
                    )
            self._response.data = items
        return self._response


class AttachItems(BaseReportableUseCae):
    CHUNK_SIZE = 500

    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        folder: FolderEntity,
        attachments: List[AttachmentEntity],
        annotation_status: str,
        backend_service_provider: SuperannotateServiceProvider,
        upload_state_code: int = constances.UploadState.EXTERNAL.value,
    ):
        super().__init__(reporter)
        self._project = project
        self._folder = folder
        self._attachments = attachments
        self._annotation_status_code = constances.AnnotationStatus.get_value(annotation_status)
        self._upload_state_code = upload_state_code
        self._backend_service = backend_service_provider
        self._attachments_count = None

    @property
    def attachments_count(self):
        if not self._attachments_count:
            self._attachments_count = len(self._attachments)
        return self._attachments_count

    def validate_limitations(self):
        attachments_count = self.attachments_count
        response = self._backend_service.get_limitations(
            team_id=self._project.team_id,
            project_id=self._project.uuid,
            folder_id=self._folder.uuid,
        )
        if not response.ok:
            raise AppValidationException(response.error)
        if attachments_count > response.data.folder_limit.remaining_image_count:
            raise AppValidationException(constances.ATTACH_FOLDER_LIMIT_ERROR_MESSAGE)
        elif attachments_count > response.data.project_limit.remaining_image_count:
            raise AppValidationException(constances.ATTACH_PROJECT_LIMIT_ERROR_MESSAGE)
        elif (
                response.data.user_limit
                and attachments_count > response.data.user_limit.remaining_image_count
        ):
            raise AppValidationException(constances.ATTACH_USER_LIMIT_ERROR_MESSAGE)

    def validate_upload_state(self):
        if self._project.upload_state == constances.UploadState.BASIC.value:
            raise AppValidationException(constances.ATTACHING_UPLOAD_STATE_ERROR)

    @staticmethod
    def generate_meta():
        return {
            "width": None,
            "height": None
        }

    def execute(self) -> Response:
        if self.is_valid():
            duplications = []
            attached = []
            self.reporter.start_progress(self.attachments_count, description="Attaching URLs")

            for i in range(0, self.attachments_count, self.CHUNK_SIZE):
                attachments = self._attachments[i : i + self.CHUNK_SIZE]  # noqa: E203
                response = self._backend_service.get_bulk_images(
                    project_id=self._project.uuid,
                    team_id=self._project.team_id,
                    folder_id=self._folder.uuid,
                    images=[attachment.name for attachment in attachments],
                )
                if isinstance(response, dict) and "error" in response:
                    raise AppException(response["error"])
                duplications.extend([image["name"] for image in response])
                to_upload = []
                to_upload_meta = {}
                for attachment in attachments:
                    if attachment.name not in duplications:
                        to_upload.append({"name": attachment.name, "url": attachment.url})
                        to_upload_meta[attachment.name] = self.generate_meta()
                if to_upload:
                    backend_response = self._backend_service.attach_files(
                        project_id=self._project.uuid,
                        folder_id=self._folder.uuid,
                        team_id=self._project.team_id,
                        files=to_upload,
                        annotation_status_code=self._annotation_status_code,
                        upload_state_code=self._upload_state_code,
                        meta=to_upload_meta
                    )
                    if "error" in backend_response:
                        self._response.errors = AppException(backend_response["error"])
                    else:
                        attached.extend(backend_response)
                        self.reporter.update_progress(len(attachments))
            self.reporter.finish_progress()
            self._response.data = attached, duplications
        return self._response
