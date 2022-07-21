import copy
from typing import List
from typing import Optional

import superannotate.lib.core as constants
from lib.core.conditions import Condition
from lib.core.conditions import CONDITION_EQ as EQ
from lib.core.entities import AttachmentEntity
from lib.core.entities import BaseItemEntity
from lib.core.entities import DocumentEntity
from lib.core.entities import FolderEntity
from lib.core.entities import ImageEntity
from lib.core.entities import ProjectEntity
from lib.core.entities import SubSetEntity
from lib.core.entities import TmpImageEntity
from lib.core.entities import VideoEntity
from lib.core.exceptions import AppException
from lib.core.exceptions import AppValidationException
from lib.core.exceptions import BackendError
from lib.core.reporter import Reporter
from lib.core.repositories import BaseReadOnlyRepository
from lib.core.response import Response
from lib.core.serviceproviders import SuperannotateServiceProvider
from lib.core.usecases.base import BaseReportableUseCase
from lib.core.usecases.base import BaseUseCase
from superannotate.logger import get_default_logger

logger = get_default_logger()


class GetBulkItems(BaseUseCase):
    def __init__(
        self,
        service: SuperannotateServiceProvider,
        project_id: int,
        team_id: int,
        folder_id: int,
        items: List[str],
    ):
        super().__init__()
        self._service = service
        self._project_id = project_id
        self._team_id = team_id
        self._folder_id = folder_id
        self._items = items
        self._chunk_size = 500

    def execute(self):
        res = []
        for i in range(0, len(self._items), self._chunk_size):
            response = self._service.get_bulk_items(
                project_id=self._project_id,
                team_id=self._team_id,
                folder_id=self._folder_id,
                items=self._items[i : i + self._chunk_size],  # noqa: E203
            )

            if not response.ok:
                raise AppException(response.error)
            # TODO stop using Image Entity when it gets deprecated and from_dict gets implemented for items
            res += [ImageEntity.from_dict(**item) for item in response.data]
        self._response.data = res
        return self._response


class GetItem(BaseReportableUseCase):
    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        folder: FolderEntity,
        backend_client: SuperannotateServiceProvider,
        item_name: str,
        include_custom_metadata: bool,
    ):
        super().__init__(reporter)
        self._project = project
        self._folder = folder
        self._backend_client = backend_client
        self._item_name = item_name
        self._include_custom_metadata = include_custom_metadata

    def validate_project_type(self):
        if (
            self._project.type == constants.ProjectType.PIXEL.value
            and self._include_custom_metadata
        ):
            raise AppException(constants.METADATA_DEPRICATED_FOR_PIXEL)

    @staticmethod
    def serialize_entity(entity: BaseItemEntity, project: ProjectEntity):
        entity = BaseItemEntity(**BaseItemEntity.map_fields(entity.dict()))
        if project.upload_state != constants.UploadState.EXTERNAL.value:
            entity.url = None
        if project.type in (
            constants.ProjectType.VECTOR.value,
            constants.ProjectType.PIXEL.value,
        ):
            tmp_entity = entity
            if project.type == constants.ProjectType.VECTOR.value:
                entity.segmentation_status = None
            if project.upload_state == constants.UploadState.EXTERNAL.value:
                tmp_entity.prediction_status = None
                tmp_entity.segmentation_status = None
            return TmpImageEntity(**tmp_entity.dict(by_alias=True))
        elif project.type == constants.ProjectType.VIDEO.value:
            return VideoEntity(**entity.dict(by_alias=True))
        elif project.type == constants.ProjectType.DOCUMENT.value:
            return DocumentEntity(**entity.dict(by_alias=True))
        return entity

    def execute(self) -> Response:
        if self.is_valid():
            condition = (
                Condition("name", self._item_name, EQ)
                & Condition("team_id", self._project.team_id, EQ)
                & Condition("project_id", self._project.id, EQ)
                & Condition("folder_id", self._folder.uuid, EQ)
                & Condition("includeCustomMetadata", self._include_custom_metadata, EQ)
            )
            response = self._backend_client.list_items(condition.build_query())
            if not response.ok:
                self._response.errors = response.error
                return self._response
            entity = next((i for i in response.data if i.name == self._item_name), None)
            if entity:
                entity = self.serialize_entity(entity, self._project)
                entity.add_path(self._project.name, self._folder.name)
                self._response.data = entity
            else:
                self._response.errors = AppException("Item not found.")
        return self._response


class QueryEntitiesUseCase(BaseReportableUseCase):
    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        folder: FolderEntity,
        backend_service_provider: SuperannotateServiceProvider,
        query: str,
        subset: str,
    ):
        super().__init__(reporter)
        self._project = project
        self._folder = folder
        self._backend_client = backend_service_provider
        self._query = query
        self._subset = subset

    def validate_arguments(self):
        if self._query:
            response = self._backend_client.validate_saqul_query(
                self._project.team_id, self._project.id, self._query
            )
            if response.get("error"):
                raise AppException(response["error"])
            if response["isValidQuery"]:
                self._query = response["parsedQuery"]
            else:
                raise AppException("Incorrect query.")
        else:
            response = self._backend_client.validate_saqul_query(
                self._project.team_id, self._project.id, "-"
            )
            if response.get("error"):
                raise AppException(response["error"])

        if not any([self._query, self._subset]):
            raise AppException(
                "The query and subset params cannot have the value None at the same time."
            )
        if self._subset and not self._folder.is_root:
            raise AppException(
                "The folder name should be specified in the query string."
            )

    def execute(self) -> Response:
        if self.is_valid():
            query_kwargs = {}
            if self._subset:
                subset: Optional[SubSetEntity] = None
                response = self._backend_client.list_sub_sets(
                    team_id=self._project.team_id, project_id=self._project.id
                )
                if response.ok:
                    subset = next(
                        (_sub for _sub in response.data if _sub.name == self._subset),
                        None,
                    )
                if not subset:
                    self._response.errors = AppException(
                        "Subset not found. Use the superannotate."
                        "get_subsets() function to get a list of the available subsets."
                    )
                    return self._response
                query_kwargs["subset_id"] = subset.id
            if self._query:
                query_kwargs["query"] = self._query
            query_kwargs["folder_id"] = (
                None if self._folder.name == "root" else self._folder.uuid
            )
            service_response = self._backend_client.saqul_query(
                self._project.team_id,
                self._project.id,
                **query_kwargs,
            )
            if service_response.ok:
                data = []
                for i, item in enumerate(service_response.data):
                    tmp_item = GetItem.serialize_entity(BaseItemEntity(**item), self._project)
                    folder_path = f"{'/' + item['folder_name'] if not item['is_root_folder'] else ''}"
                    tmp_item.path = f"{self._project.name}" + folder_path
                    data.append(tmp_item)
                self._response.data = data
            else:
                self._response.errors = service_response.data
        return self._response


class ListItems(BaseReportableUseCase):
    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        folder: FolderEntity,
        folders: BaseReadOnlyRepository,
        search_condition: Condition,
        backend_client: SuperannotateServiceProvider,
        recursive: bool = False,
        include_custom_metadata: bool = False,
    ):
        super().__init__(reporter)
        self._project = project
        self._folders = folders
        self._folder = folder
        self._backend_client = backend_client
        self._search_condition = search_condition
        self._recursive = recursive
        self._include_custom_metadata = include_custom_metadata

    def validate_recursive_case(self):
        if not self._folder.is_root and self._recursive:
            self._recursive = False

    def validate_project_type(self):
        if (
            self._project.type == constants.ProjectType.PIXEL.value
            and self._include_custom_metadata
        ):
            raise AppException(constants.METADATA_DEPRICATED_FOR_PIXEL)

    def execute(self) -> Response:
        if self.is_valid():
            self._search_condition &= Condition("team_id", self._project.team_id, EQ)
            self._search_condition &= Condition("project_id", self._project.id, EQ)
            self._search_condition &= Condition(
                "includeCustomMetadata", self._include_custom_metadata, EQ
            )

            if not self._recursive:
                self._search_condition &= Condition("folder_id", self._folder.uuid, EQ)
                items_response = self._backend_client.list_items(
                    self._search_condition.build_query()
                )
                if not items_response.ok:
                    raise AppException(items_response.error)
                items = []
                for item in items_response.data:
                    item = GetItem.serialize_entity(item, self._project)
                    item.add_path(self._project.name, self._folder.name)
                    items.append(item)
            else:
                items = []
                folders = self._folders.get_all(
                    Condition("team_id", self._project.team_id, EQ)
                    & Condition("project_id", self._project.id, EQ),
                )
                folders.append(self._folder)
                for folder in folders:
                    response = self._backend_client.list_items(
                        (
                            copy.deepcopy(self._search_condition)
                            & Condition("folder_id", folder.uuid, EQ)
                        ).build_query()
                    )
                    if not response.ok:
                        raise AppException(response.error)
                    for item in response.data:
                        item = GetItem.serialize_entity(item, self._project)
                        item.add_path(self._project.name, folder.name)
                        items.append(item)
            self._response.data = items
        return self._response


class AssignItemsUseCase(BaseUseCase):
    CHUNK_SIZE = 500

    def __init__(
        self,
        service: SuperannotateServiceProvider,
        project: ProjectEntity,
        folder: FolderEntity,
        item_names: list,
        user: str,
    ):
        super().__init__()
        self._project = project
        self._folder = folder
        self._item_names = item_names
        self._user = user
        self._service = service

    def validate_item_names(
        self,
    ):
        self._item_names = list(set(self._item_names))

    def execute(self):
        cnt_assigned = 0
        total_count = len(self._item_names)
        if self.is_valid():
            for i in range(0, len(self._item_names), self.CHUNK_SIZE):
                response = self._service.assign_items(
                    team_id=self._project.team_id,
                    project_id=self._project.id,
                    folder_name=self._folder.name,
                    user=self._user,
                    item_names=self._item_names[i : i + self.CHUNK_SIZE],  # noqa: E203
                )
                if not response.ok and response.error:  # User not found
                    self._response.errors += response.error
                    return self._response

                cnt_assigned += response.data["successCount"]
            logger.info(
                f"Assigned {cnt_assigned}/{total_count} items to user {self._user}"
            )
        return self._response


class UnAssignItemsUseCase(BaseUseCase):
    CHUNK_SIZE = 500

    def __init__(
        self,
        service: SuperannotateServiceProvider,
        project_entity: ProjectEntity,
        folder: FolderEntity,
        item_names: list,
    ):
        super().__init__()
        self._project_entity = project_entity
        self._folder = folder
        self._item_names = item_names
        self._service = service

    def execute(self):
        # todo handling to backend side
        for i in range(0, len(self._item_names), self.CHUNK_SIZE):
            is_un_assigned = self._service.un_assign_items(
                team_id=self._project_entity.team_id,
                project_id=self._project_entity.id,
                folder_name=self._folder.name,
                item_names=self._item_names[i : i + self.CHUNK_SIZE],  # noqa: E203
            )
            if not is_un_assigned:
                self._response.errors = AppException(
                    f"Cant un assign {', '.join(self._item_names[i: i + self.CHUNK_SIZE])}"
                )

        return self._response


class AttachItems(BaseReportableUseCase):
    CHUNK_SIZE = 500

    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        folder: FolderEntity,
        attachments: List[AttachmentEntity],
        annotation_status: str,
        backend_service_provider: SuperannotateServiceProvider,
        upload_state_code: int = constants.UploadState.EXTERNAL.value,
    ):
        super().__init__(reporter)
        self._project = project
        self._folder = folder
        self._attachments = attachments
        self._annotation_status_code = constants.AnnotationStatus.get_value(
            annotation_status
        )
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
            project_id=self._project.id,
            folder_id=self._folder.uuid,
        )
        if not response.ok:
            raise AppValidationException(response.error)
        if attachments_count > response.data.folder_limit.remaining_image_count:
            raise AppValidationException(constants.ATTACH_FOLDER_LIMIT_ERROR_MESSAGE)
        elif attachments_count > response.data.project_limit.remaining_image_count:
            raise AppValidationException(constants.ATTACH_PROJECT_LIMIT_ERROR_MESSAGE)
        elif (
            response.data.user_limit
            and attachments_count > response.data.user_limit.remaining_image_count
        ):
            raise AppValidationException(constants.ATTACH_USER_LIMIT_ERROR_MESSAGE)

    def validate_upload_state(self):
        if self._project.upload_state == constants.UploadState.BASIC.value:
            raise AppValidationException(constants.ATTACHING_UPLOAD_STATE_ERROR)

    @staticmethod
    def generate_meta():
        return {"width": None, "height": None}

    def execute(self) -> Response:
        if self.is_valid():
            duplications = []
            attached = []
            self.reporter.start_progress(self.attachments_count, "Attaching URLs")
            for i in range(0, self.attachments_count, self.CHUNK_SIZE):
                attachments = self._attachments[i : i + self.CHUNK_SIZE]  # noqa: E203
                response = self._backend_service.get_bulk_images(
                    project_id=self._project.id,
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
                        to_upload.append(
                            {"name": attachment.name, "path": attachment.url}
                        )
                        to_upload_meta[attachment.name] = self.generate_meta()
                if to_upload:
                    backend_response = self._backend_service.attach_files(
                        project_id=self._project.id,
                        folder_id=self._folder.uuid,
                        team_id=self._project.team_id,
                        files=to_upload,
                        annotation_status_code=self._annotation_status_code,
                        upload_state_code=self._upload_state_code,
                        meta=to_upload_meta,
                    )
                    if "error" in backend_response:
                        self._response.errors = AppException(backend_response["error"])
                    else:
                        attached.extend(backend_response)
                self.reporter.update_progress(len(attachments))
            self.reporter.finish_progress()
            self._response.data = attached, duplications
        return self._response


class CopyItems(BaseReportableUseCase):
    """
    Copy items in bulk between folders in a project.
    Return skipped item names.
    """

    CHUNK_SIZE = 500

    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        from_folder: FolderEntity,
        to_folder: FolderEntity,
        item_names: List[str],
        items: BaseReadOnlyRepository,
        backend_service_provider: SuperannotateServiceProvider,
        include_annotations: bool,
    ):
        super().__init__(reporter)
        self._project = project
        self._from_folder = from_folder
        self._to_folder = to_folder
        self._item_names = item_names
        self._items = items
        self._backend_service = backend_service_provider
        self._include_annotations = include_annotations

    def _validate_limitations(self, items_count):
        response = self._backend_service.get_limitations(
            team_id=self._project.team_id,
            project_id=self._project.id,
            folder_id=self._to_folder.uuid,
        )
        if not response.ok:
            raise AppValidationException(response.error)
        if items_count > response.data.folder_limit.remaining_image_count:
            raise AppValidationException(constants.COPY_FOLDER_LIMIT_ERROR_MESSAGE)
        if items_count > response.data.project_limit.remaining_image_count:
            raise AppValidationException(constants.COPY_PROJECT_LIMIT_ERROR_MESSAGE)

    def validate_item_names(self):
        if self._item_names:
            self._item_names = list(set(self._item_names))

    def execute(self):
        if self.is_valid():
            if self._item_names:
                items = self._item_names
            else:
                condition = (
                    Condition("team_id", self._project.team_id, EQ)
                    & Condition("project_id", self._project.id, EQ)
                    & Condition("folder_id", self._from_folder.uuid, EQ)
                )
                items = [item.name for item in self._items.get_all(condition)]

            existing_items = []
            for i in range(0, len(items), self.CHUNK_SIZE):
                cand_items = self._backend_service.get_bulk_images(
                    project_id=self._project.id,
                    team_id=self._project.team_id,
                    folder_id=self._to_folder.uuid,
                    images=items[i : i + self.CHUNK_SIZE],
                )
                if isinstance(cand_items, dict):
                    continue
                existing_items += cand_items

            duplications = [item["name"] for item in existing_items]
            items_to_copy = list(set(items) - set(duplications))
            skipped_items = duplications
            try:
                self._validate_limitations(len(items_to_copy))
            except AppValidationException as e:
                self._response.errors = e
                return self._response
            if items_to_copy:
                for i in range(0, len(items_to_copy), self.CHUNK_SIZE):
                    chunk_to_copy = items_to_copy[i : i + self.CHUNK_SIZE]  # noqa: E203
                    poll_id = (
                        self._backend_service.copy_items_between_folders_transaction(
                            team_id=self._project.team_id,
                            project_id=self._project.id,
                            from_folder_id=self._from_folder.uuid,
                            to_folder_id=self._to_folder.uuid,
                            items=chunk_to_copy,
                            include_annotations=self._include_annotations,
                        )
                    )
                    if not poll_id:
                        skipped_items.extend(chunk_to_copy)
                        continue
                    try:
                        self._backend_service.await_progress(
                            self._project.id,
                            self._project.team_id,
                            poll_id=poll_id,
                            items_count=len(chunk_to_copy),
                        )
                    except BackendError as e:
                        self._response.errors = AppException(e)
                        return self._response

                existing_items = []
                for i in range(0, len(items), self.CHUNK_SIZE):
                    cand_items = self._backend_service.get_bulk_images(
                        project_id=self._project.id,
                        team_id=self._project.team_id,
                        folder_id=self._to_folder.uuid,
                        images=items[i : i + self.CHUNK_SIZE],
                    )
                    if isinstance(cand_items, dict):
                        continue
                    existing_items += cand_items

                existing_item_names_set = {item["name"] for item in existing_items}
                items_to_copy_names_set = set(items_to_copy)
                copied_items = existing_item_names_set.intersection(
                    items_to_copy_names_set
                )
                skipped_items.extend(list(items_to_copy_names_set - copied_items))
                self.reporter.log_info(
                    f"Copied {len(copied_items)}/{len(items)} item(s) from "
                    f"{self._project.name}{'' if self._from_folder.is_root else f'/{self._from_folder.name}'} to "
                    f"{self._project.name}{'' if self._to_folder.is_root else f'/{self._to_folder.name}'}"
                )
            self._response.data = skipped_items
        return self._response


class MoveItems(BaseReportableUseCase):
    CHUNK_SIZE = 1000

    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        from_folder: FolderEntity,
        to_folder: FolderEntity,
        item_names: List[str],
        items: BaseReadOnlyRepository,
        backend_service_provider: SuperannotateServiceProvider,
    ):
        super().__init__(reporter)
        self._project = project
        self._from_folder = from_folder
        self._to_folder = to_folder
        self._item_names = item_names
        self._items = items
        self._backend_service = backend_service_provider

    def validate_item_names(self):
        if self._item_names:
            self._item_names = list(set(self._item_names))

    def _validate_limitations(self, items_count):
        response = self._backend_service.get_limitations(
            team_id=self._project.team_id,
            project_id=self._project.id,
            folder_id=self._to_folder.uuid,
        )
        if not response.ok:
            raise AppValidationException(response.error)
        if items_count > response.data.folder_limit.remaining_image_count:
            raise AppValidationException(constants.MOVE_FOLDER_LIMIT_ERROR_MESSAGE)
        if items_count > response.data.project_limit.remaining_image_count:
            raise AppValidationException(constants.MOVE_PROJECT_LIMIT_ERROR_MESSAGE)

    def execute(self):
        if self.is_valid():
            if not self._item_names:
                condition = (
                    Condition("team_id", self._project.team_id, EQ)
                    & Condition("project_id", self._project.id, EQ)
                    & Condition("folder_id", self._from_folder.uuid, EQ)
                )
                items = [item.name for item in self._items.get_all(condition)]
            else:
                items = self._item_names
            try:
                self._validate_limitations(len(items))
            except AppValidationException as e:
                self._response.errors = e
                return self._response
            moved_images = []
            for i in range(0, len(items), self.CHUNK_SIZE):
                moved_images.extend(
                    self._backend_service.move_images_between_folders(
                        team_id=self._project.team_id,
                        project_id=self._project.id,
                        from_folder_id=self._from_folder.uuid,
                        to_folder_id=self._to_folder.uuid,
                        images=items[i : i + self.CHUNK_SIZE],  # noqa: E203
                    )
                )
            self.reporter.log_info(
                f"Moved {len(moved_images)}/{len(items)} item(s) from "
                f"{self._project.name}{'' if self._from_folder.is_root else f'/{self._from_folder.name}'} to "
                f"{self._project.name}{'' if self._to_folder.is_root else f'/{self._to_folder.name}'}"
            )

            self._response.data = list(set(items) - set(moved_images))
        return self._response


class SetAnnotationStatues(BaseReportableUseCase):
    CHUNK_SIZE = 500
    ERROR_MESSAGE = "Failed to change status"

    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        folder: FolderEntity,
        items: BaseReadOnlyRepository,
        annotation_status: str,
        backend_service_provider: SuperannotateServiceProvider,
        item_names: List[str] = None,
    ):
        super().__init__(reporter)
        self._project = project
        self._folder = folder
        self._item_names = item_names
        self._items = items
        self._annotation_status_code = constants.AnnotationStatus.get_value(
            annotation_status
        )
        self._backend_service = backend_service_provider

    def validate_items(self):
        if not self._item_names:
            condition = (
                Condition("team_id", self._project.team_id, EQ)
                & Condition("project_id", self._project.id, EQ)
                & Condition("folder_id", self._folder.uuid, EQ)
            )
            self._item_names = [item.name for item in self._items.get_all(condition)]
            return
        existing_items = []
        for i in range(0, len(self._item_names), self.CHUNK_SIZE):

            search_names = self._item_names[i : i + self.CHUNK_SIZE]
            cand_items = self._backend_service.get_bulk_images(
                project_id=self._project.id,
                team_id=self._project.team_id,
                folder_id=self._folder.uuid,
                images=search_names,
            )

            if isinstance(cand_items, dict):
                continue
            existing_items += cand_items

        if not existing_items:
            raise AppValidationException(self.ERROR_MESSAGE)
        if existing_items:
            self._item_names = list(
                {i["name"] for i in existing_items}.intersection(set(self._item_names))
            )

    def execute(self):
        if self.is_valid():
            for i in range(0, len(self._item_names), self.CHUNK_SIZE):
                status_changed = self._backend_service.set_images_statuses_bulk(
                    image_names=self._item_names[
                        i : i + self.CHUNK_SIZE
                    ],  # noqa: E203,
                    team_id=self._project.team_id,
                    project_id=self._project.id,
                    folder_id=self._folder.uuid,
                    annotation_status=self._annotation_status_code,
                )
                if not status_changed:
                    self._response.errors = AppException(self.ERROR_MESSAGE)
                    break
        return self._response


class DeleteItemsUseCase(BaseUseCase):
    CHUNK_SIZE = 1000

    def __init__(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        backend_service_provider: SuperannotateServiceProvider,
        items: BaseReadOnlyRepository,
        item_names: List[str] = None,
    ):
        super().__init__()
        self._project = project
        self._folder = folder
        self._items = items
        self._backend_service = backend_service_provider
        self._item_names = item_names

    def execute(self):
        if self.is_valid():
            if self._item_names:
                item_ids = [
                    item.uuid
                    for item in GetBulkItems(
                        service=self._backend_service,
                        project_id=self._project.id,
                        team_id=self._project.team_id,
                        folder_id=self._folder.uuid,
                        items=self._item_names,
                    )
                    .execute()
                    .data
                ]
            else:
                condition = (
                    Condition("team_id", self._project.team_id, EQ)
                    & Condition("project_id", self._project.id, EQ)
                    & Condition("folder_id", self._folder.uuid, EQ)
                )
                item_ids = [item.id for item in self._items.get_all(condition)]

            for i in range(0, len(item_ids), self.CHUNK_SIZE):
                response = self._backend_service.delete_items(
                    project_id=self._project.id,
                    team_id=self._project.team_id,
                    item_ids=item_ids[i : i + self.CHUNK_SIZE],  # noqa: E203
                )

            logger.info(
                f"Items deleted in project {self._project.name}{'/' + self._folder.name if not self._folder.is_root else ''}"
            )

        return self._response
