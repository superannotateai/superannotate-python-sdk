import logging
import re
import traceback
from collections import defaultdict
from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor
from typing import Dict
from typing import Generator
from typing import List
from typing import Union

import lib.core as constants
from lib.core.conditions import Condition
from lib.core.conditions import CONDITION_EQ as EQ
from lib.core.entities import AttachmentEntity
from lib.core.entities import BaseItemEntity
from lib.core.entities import DocumentEntity
from lib.core.entities import FolderEntity
from lib.core.entities import ImageEntity
from lib.core.entities import ProjectEntity
from lib.core.entities import VideoEntity
from lib.core.entities.items import MultiModalItemEntity
from lib.core.exceptions import AppException
from lib.core.exceptions import AppValidationException
from lib.core.exceptions import BackendError
from lib.core.jsx_conditions import EmptyQuery
from lib.core.jsx_conditions import Filter
from lib.core.jsx_conditions import OperatorEnum
from lib.core.reporter import Reporter
from lib.core.response import Response
from lib.core.serviceproviders import BaseServiceProvider
from lib.core.types import Attachment
from lib.core.types import AttachmentMeta
from lib.core.usecases.base import BaseReportableUseCase
from lib.core.usecases.base import BaseUseCase
from lib.core.usecases.folders import SearchFoldersUseCase
from lib.infrastructure.utils import divide_to_chunks
from lib.infrastructure.utils import extract_project_folder
from typing_extensions import Literal

logger = logging.getLogger("sa")


def serialize_item_entity(
    entity: Union[BaseItemEntity, dict], project: ProjectEntity, map_fields: bool = True
) -> BaseItemEntity:
    if isinstance(entity, BaseItemEntity):
        entity = entity.dict()
    if map_fields:
        entity = BaseItemEntity.map_fields(entity)
    entity = BaseItemEntity(**entity)
    if project.upload_state != constants.UploadState.EXTERNAL.value:
        entity.url = None
    if project.type in constants.ProjectType.images:
        tmp_entity = entity
        if project.type == constants.ProjectType.VECTOR.value:
            entity.segmentation_status = None
        if project.upload_state == constants.UploadState.EXTERNAL.value:
            tmp_entity.prediction_status = None
            tmp_entity.segmentation_status = None
        return ImageEntity(**tmp_entity.dict(by_alias=True))
    elif project.type == constants.ProjectType.VIDEO.value:
        return VideoEntity(**entity.dict(by_alias=True))
    elif project.type == constants.ProjectType.DOCUMENT.value:
        return DocumentEntity(**entity.dict(by_alias=True))
    elif project.type == constants.ProjectType.MULTIMODAL.value:
        return MultiModalItemEntity(**entity.dict(by_alias=True))
    return entity


def add_item_path(project: ProjectEntity, folder: FolderEntity, item: BaseItemEntity):
    item.path = f"{project.name}{'' if folder.is_root else f'/{folder.name}'}"
    return item


class QueryEntitiesUseCase(BaseReportableUseCase):
    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        folder: FolderEntity,
        service_provider: BaseServiceProvider,
        query: str,
        subset: str = None,
    ):
        super().__init__(reporter)
        self._project = project
        self._folder = folder
        self._service_provider = service_provider
        self._query = query
        self._subset = subset

    def validate_arguments(self):
        if self._query:
            response = self._service_provider.explore.validate_saqul_query(
                project=self._project, query=self._query
            )

            if not response.ok:
                raise AppException(response.error)
            if response.data["isValidQuery"]:
                self._query = response.data["parsedQuery"]
            else:
                raise AppException("Incorrect query.")
        else:
            response = self._service_provider.explore.validate_saqul_query(
                self._project, "-"
            )
            if not response.ok:
                raise AppException(response.error)

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
                response = self._service_provider.explore.list_subsets(self._project)
                if response.ok:
                    subset = next(
                        (_sub for _sub in response.data if _sub.name == self._subset),
                        None,
                    )
                else:
                    self._response.errors = response.error
                    return self._response
                if not subset:
                    self._response.errors = AppException(
                        "Subset not found. Use the superannotate."
                        "get_subsets() function to get a list of the available subsets."
                    )
                    return self._response
                query_kwargs["subset_id"] = subset.id
            if self._query:
                query_kwargs["query"] = self._query
            query_kwargs["folder"] = (
                None if self._folder.name == "root" else self._folder
            )
            service_response = self._service_provider.explore.saqul_query(
                self._project,
                **query_kwargs,
            )
            if service_response.ok:
                data = []
                for i, item in enumerate(service_response.data):
                    #  tmp wrapper
                    if "assignment" in item:
                        item["assignments"] = item.pop("assignment")
                    item["url"] = item.get("path", None)
                    item["path"] = (
                        f"{self._project.name}"
                        f"{'/' + item['folder_name'] if not item['is_root_folder'] else ''}"
                    )
                    data.append(item)
                self._response.data = data
            else:
                self._response.errors = service_response.data
        return self._response


class QueryEntitiesCountUseCase(BaseReportableUseCase):
    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        service_provider: BaseServiceProvider,
        query: str,
    ):
        super().__init__(reporter)
        self._project = project
        self._service_provider = service_provider
        self._query = query

    def validate_arguments(self):
        if self._query:
            response = self._service_provider.explore.validate_saqul_query(
                project=self._project, query=self._query
            )

            if not response.ok:
                raise AppException(response.error)
            if response.data["isValidQuery"]:
                self._query = response.data["parsedQuery"]
            else:
                raise AppException("Incorrect query.")
        else:
            response = self._service_provider.explore.validate_saqul_query(
                self._project, "-"
            )
            if not response.ok:
                raise AppException(response.error)

    def execute(self) -> Response:
        if self.is_valid():
            query_kwargs = {"query": self._query}
            service_response = self._service_provider.explore.query_item_count(
                self._project,
                **query_kwargs,
            )
            if service_response.ok:
                self._response.data = service_response.data
            else:
                self._response.errors = service_response.data
        return self._response


class AssignItemsUseCase(BaseUseCase):
    CHUNK_SIZE = 500

    def __init__(
        self,
        service_provider: BaseServiceProvider,
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
        self._service_provider = service_provider

    def validate_item_names(
        self,
    ):
        self._item_names = list(set(self._item_names))

    def execute(self):
        cnt_assigned = 0
        total_count = len(self._item_names)
        if self.is_valid():
            for i in range(0, len(self._item_names), self.CHUNK_SIZE):
                response = self._service_provider.projects.assign_items(
                    project=self._project,
                    folder=self._folder,
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
        service_provider: BaseServiceProvider,
        project: ProjectEntity,
        folder: FolderEntity,
        item_names: list,
    ):
        super().__init__()
        self._project = project
        self._folder = folder
        self._item_names = item_names
        self._service_provider = service_provider

    def execute(self):
        # todo handling to backend side
        for i in range(0, len(self._item_names), self.CHUNK_SIZE):
            response = self._service_provider.projects.un_assign_items(
                project=self._project,
                folder=self._folder,
                item_names=self._item_names[i : i + self.CHUNK_SIZE],  # noqa: E203
            )
            if not response.ok:
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
        service_provider: BaseServiceProvider,
        annotation_status_value: int = None,
        upload_state_code: int = constants.UploadState.EXTERNAL.value,
    ):
        super().__init__(reporter)
        self._project = project
        self._folder = folder
        self._attachments = attachments
        self._annotation_status_code = annotation_status_value
        self._upload_state_code = upload_state_code
        self._service_provider = service_provider
        self._attachments_count = None

    @property
    def attachments_count(self):
        if not self._attachments_count:
            self._attachments_count = len(self._attachments)
        return self._attachments_count

    def validate_limitations(self):
        attachments_count = self.attachments_count
        response = self._service_provider.get_limitations(
            project=self._project, folder=self._folder
        )
        if not response.ok:
            raise AppValidationException(response.error)
        if attachments_count > response.data.folder_limit.remaining_image_count:
            raise AppValidationException(constants.ATTACH_FOLDER_LIMIT_ERROR_MESSAGE)
        if attachments_count > response.data.project_limit.remaining_image_count:
            raise AppValidationException(constants.ATTACH_PROJECT_LIMIT_ERROR_MESSAGE)
        if (
            response.data.user_limit
            and attachments_count > response.data.user_limit.remaining_image_count
        ):
            raise AppValidationException(constants.ATTACH_USER_LIMIT_ERROR_MESSAGE)

    def validate_upload_state(self):
        if self._project.upload_state == constants.UploadState.BASIC.value:
            raise AppValidationException(constants.ATTACHING_UPLOAD_STATE_ERROR)

    @staticmethod
    def generate_meta(integration_id=None) -> AttachmentMeta:
        return AttachmentMeta(width=None, height=None, integration_id=integration_id)

    def execute(self) -> Response:
        if self.is_valid():
            duplications = []
            attached = []
            self.reporter.start_progress(self.attachments_count, "Attaching URLs")
            for i in range(0, self.attachments_count, self.CHUNK_SIZE):
                attachments = self._attachments[i : i + self.CHUNK_SIZE]  # noqa: E203

                query = Filter(
                    "name",
                    [attachment.name for attachment in attachments],
                    OperatorEnum.IN,
                )
                data = self._service_provider.item_service.list(
                    self._project.id, self._folder.id, query
                )

                duplications.extend([image.name for image in data])
                to_upload: List[Attachment] = []
                to_upload_meta: Dict[str, AttachmentMeta] = {}
                for attachment in attachments:
                    if attachment.name not in duplications:
                        to_upload.append(
                            Attachment(name=attachment.name, path=attachment.url)
                        )
                        to_upload_meta[attachment.name] = self.generate_meta(
                            attachment.integration_id
                        )
                if to_upload:
                    backend_response = self._service_provider.items.attach(
                        project=self._project,
                        folder=self._folder,
                        attachments=to_upload,
                        annotation_status_code=self._annotation_status_code,
                        upload_state_code=self._upload_state_code,
                        meta=to_upload_meta,
                    )
                    if not backend_response.ok:
                        self._response.errors = AppException(backend_response.error)
                    else:
                        attached.extend([i.name for i in to_upload])
                self.reporter.update_progress(len(attachments))
            self.reporter.finish_progress()
            self._response.data = attached, duplications
        return self._response


class GenerateItems(BaseReportableUseCase):
    CHUNK_SIZE = 500
    INVALID_CHARS_PATTERN = re.compile(r"[<>:\"'/\\|?*&$!+]")

    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        folder: FolderEntity,
        name_prefix: str,
        count: int,
        service_provider: BaseServiceProvider,
    ):
        super().__init__(reporter)
        self._project = project
        self._folder = folder
        self._name_prefix = name_prefix
        self._count = count
        self._service_provider = service_provider

    def validate_name(self):
        if (
            len(self._name_prefix) > 114
            or self.INVALID_CHARS_PATTERN.search(self._name_prefix) is not None
        ):
            raise AppException("Invalid item name.")

    def validate_limitations(self):
        response = self._service_provider.get_limitations(
            project=self._project, folder=self._folder
        )
        if not response.ok:
            raise AppValidationException(response.error)
        if self._count > response.data.folder_limit.remaining_image_count:
            raise AppValidationException(constants.ATTACH_FOLDER_LIMIT_ERROR_MESSAGE)
        if self._count > response.data.project_limit.remaining_image_count:
            raise AppValidationException(constants.ATTACH_PROJECT_LIMIT_ERROR_MESSAGE)
        if (
            response.data.user_limit
            and self._count > response.data.user_limit.remaining_image_count
        ):
            raise AppValidationException(constants.ATTACH_USER_LIMIT_ERROR_MESSAGE)

    def validate_project_type(self):
        if self._project.type != constants.ProjectType.MULTIMODAL:
            raise AppException(
                "This function is only supported for Multimodal projects."
            )

    @staticmethod
    def generate_attachments(
        name: str, start: int, end: int, chunk_size: int
    ) -> Generator[List[Attachment], None, None]:
        chunk = []
        for i in range(start, end + 1):
            chunk.append(Attachment(name=f"{name}_{i:05d}", path="custom_llm"))
            if len(chunk) == chunk_size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk

    def execute(self) -> Response:
        if self.is_valid():
            attached_items_count = 0
            for chunk in self.generate_attachments(
                self._name_prefix, start=1, end=self._count, chunk_size=self.CHUNK_SIZE
            ):
                backend_response = self._service_provider.items.attach(
                    project=self._project,
                    folder=self._folder,
                    attachments=chunk,
                    upload_state_code=3,
                )
                if not backend_response.ok:
                    self._response.errors = AppException(backend_response.error)
                    return self._response
                attached_items_count += len(chunk)
            self._response.data = attached_items_count
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
        service_provider: BaseServiceProvider,
        include_annotations: bool,
    ):
        super().__init__(reporter)
        self._project = project
        self._from_folder = from_folder
        self._to_folder = to_folder
        self._item_names = item_names
        self._service_provider = service_provider
        self._include_annotations = include_annotations

    def _validate_limitations(self, items_count):
        response = self._service_provider.get_limitations(
            project=self._project,
            folder=self._to_folder,
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
                data = self._service_provider.item_service.list(
                    self._project.id, self._from_folder.id, EmptyQuery()
                )
                items = [i.name for i in data]
            existing_items = []
            for i in range(0, len(items), self.CHUNK_SIZE):
                query = Filter(
                    "name", items[i : i + self.CHUNK_SIZE], OperatorEnum.IN
                )  # noqa
                data = self._service_provider.item_service.list(
                    self._project.id, self._to_folder.id, query
                )
                if not data:
                    continue
                existing_items += data
            duplications = [item.name for item in existing_items]
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
                    response = self._service_provider.items.copy_multiple(
                        project=self._project,
                        from_folder=self._from_folder,
                        to_folder=self._to_folder,
                        item_names=chunk_to_copy,
                        include_annotations=self._include_annotations,
                    )
                    if not response.ok or not response.data.get("poll_id"):
                        skipped_items.extend(chunk_to_copy)
                        continue
                    try:
                        self._service_provider.items.await_copy(
                            project=self._project,
                            poll_id=response.data["poll_id"],
                            items_count=len(chunk_to_copy),
                        )
                    except BackendError as e:
                        self._response.errors = AppException(e)
                        return self._response
                existing_items = []
                for i in range(0, len(items), self.CHUNK_SIZE):
                    data = self._service_provider.item_service.list(
                        self._project.id,
                        self._to_folder.id,
                        Filter(
                            "name", items[i : i + self.CHUNK_SIZE], OperatorEnum.IN
                        ),  # noqa
                    )
                    existing_items += data

                existing_item_names_set = {item.name for item in existing_items}
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
        service_provider: BaseServiceProvider,
    ):
        super().__init__(reporter)
        self._project = project
        self._from_folder = from_folder
        self._to_folder = to_folder
        self._item_names = item_names
        self._service_provider = service_provider

    def validate_item_names(self):
        if self._item_names:
            self._item_names = list(set(self._item_names))

    def _validate_limitations(self, items_count):
        response = self._service_provider.get_limitations(
            project=self._project,
            folder=self._to_folder,
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
                items = [
                    i.name
                    for i in self._service_provider.item_service.list(
                        self._project.id, self._from_folder.id, EmptyQuery()
                    )
                ]
            else:
                items = self._item_names
            try:
                self._validate_limitations(len(items))
            except AppValidationException as e:
                self._response.errors = e
                return self._response
            moved_images = []
            for i in range(0, len(items), self.CHUNK_SIZE):
                response = self._service_provider.items.move_multiple(
                    project=self._project,
                    from_folder=self._from_folder,
                    to_folder=self._to_folder,
                    item_names=items[i : i + self.CHUNK_SIZE],  # noqa: E203
                )
                if not response.ok:
                    raise AppException(response.error)
                if response.ok and response.data.get("done"):
                    moved_images.extend(response.data["done"])

            self.reporter.log_info(
                f"Moved {len(moved_images)}/{len(items)} item(s) from "
                f"{self._project.name}{'' if self._from_folder.is_root else f'/{self._from_folder.name}'} to "
                f"{self._project.name}{'' if self._to_folder.is_root else f'/{self._to_folder.name}'}"
            )

            self._response.data = list(set(items) - set(moved_images))
        return self._response


class CopyMoveItems(BaseReportableUseCase):
    """
    Copy/Move items in bulk between folders in a project.
    Return skipped item names.
    """

    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        from_folder: FolderEntity,
        to_folder: FolderEntity,
        item_names: List[str],
        service_provider: BaseServiceProvider,
        include_annotations: bool,
        duplicate_strategy: Literal["skip", "replace", "replace_annotations_only"],
        operation: Literal["copy", "move"],
        chunk_size: int = 1000,
    ):
        super().__init__(reporter)
        self._project = project
        self._from_folder = from_folder
        self._to_folder = to_folder
        self._item_names = item_names
        self._service_provider = service_provider
        self._include_annotations = include_annotations
        self._duplicate_strategy = duplicate_strategy
        self._operation = operation
        self._chunk_size = chunk_size

    def _validate_limitations(self, items_count):
        response = self._service_provider.get_limitations(
            project=self._project,
            folder=self._to_folder,
        )
        if not response.ok:
            raise AppValidationException(response.error)
        if self._operation == "copy":
            folder_limit_err_msg = constants.COPY_FOLDER_LIMIT_ERROR_MESSAGE
            project_limit_err_msg = constants.COPY_PROJECT_LIMIT_ERROR_MESSAGE
        else:
            folder_limit_err_msg = constants.MOVE_FOLDER_LIMIT_ERROR_MESSAGE
            project_limit_err_msg = constants.MOVE_PROJECT_LIMIT_ERROR_MESSAGE
        if items_count > response.data.folder_limit.remaining_image_count:
            raise AppValidationException(folder_limit_err_msg)
        if items_count > response.data.project_limit.remaining_image_count:
            raise AppValidationException(project_limit_err_msg)

    def validate_item_names(self):
        if self._item_names:
            provided_items_count = len(self._item_names)
            self._item_names = list(set(self._item_names))
            if len(self._item_names) > provided_items_count:
                self.reporter.log_info(
                    f"Dropping duplicates. Found {len(self._item_names)}/{provided_items_count} unique items."
                )

    def execute(self):
        if self.is_valid():
            if self._item_names:
                items = self._item_names
            else:
                data = self._service_provider.item_service.list(
                    self._project.id, self._from_folder.id, EmptyQuery()
                )
                items = [i.name for i in data]
            try:
                self._validate_limitations(len(items))
            except AppValidationException as e:
                self._response.errors = e
                return self._response
            skipped_items = []
            if self._duplicate_strategy == "skip":
                existing_items = []
                for i in range(0, len(items), self._chunk_size):
                    query = Filter(
                        "name", items[i : i + self._chunk_size], OperatorEnum.IN
                    )  # noqa
                    data = self._service_provider.item_service.list(
                        self._project.id, self._to_folder.id, query
                    )
                    if not data:
                        continue
                    existing_items += data
                duplications = [item.name for item in existing_items]
                items_to_processing = list(set(items) - set(duplications))
                skipped_items.extend(duplications)
            else:
                items_to_processing = items
            if items_to_processing:
                for i in range(0, len(items_to_processing), self._chunk_size):
                    chunk_to_process = items_to_processing[
                        i : i + self._chunk_size
                    ]  # noqa: E203
                    response = self._service_provider.items.copy_move_multiple(
                        project=self._project,
                        from_folder=self._from_folder,
                        to_folder=self._to_folder,
                        item_names=chunk_to_process,
                        include_annotations=self._include_annotations,
                        duplicate_strategy=self._duplicate_strategy,
                        operation=self._operation,
                    )
                    if not response.ok or not response.data.get("poll_id"):
                        skipped_items.extend(chunk_to_process)
                        continue
                    try:
                        self._service_provider.items.await_copy_move(
                            project=self._project,
                            poll_id=response.data["poll_id"],
                            items_count=len(chunk_to_process),
                        )
                    except BackendError as e:
                        self._response.errors = AppException(e)
                        return self._response
                existing_items = []
                for i in range(0, len(items_to_processing), self._chunk_size):
                    data = self._service_provider.item_service.list(
                        self._project.id,
                        self._to_folder.id,
                        Filter(
                            "name",
                            items_to_processing[i : i + self._chunk_size],
                            OperatorEnum.IN,
                        ),  # noqa
                    )
                    existing_items += data

                existing_item_names_set = {item.name for item in existing_items}
                items_to_processing_names_set = set(items_to_processing)
                processed_items = existing_item_names_set.intersection(
                    items_to_processing_names_set
                )
                skipped_items.extend(
                    list(items_to_processing_names_set - processed_items)
                )
                operation_processing_map = {"copy": "Copied", "move": "Moved"}
                self.reporter.log_info(
                    f"{operation_processing_map[self._operation]} {len(processed_items)}/{len(items)} item(s) from "
                    f"{self._project.name}{'' if self._from_folder.is_root else f'/{self._from_folder.name}'} to "
                    f"{self._project.name}{'' if self._to_folder.is_root else f'/{self._to_folder.name}'}"
                )
            self._response.data = list(set(skipped_items))
        return self._response


class SetAnnotationStatues(BaseReportableUseCase):
    CHUNK_SIZE = 500
    ERROR_MESSAGE = "Failed to change status"

    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        folder: FolderEntity,
        annotation_status: int,
        service_provider: BaseServiceProvider,
        item_names: List[str] = None,
    ):
        super().__init__(reporter)
        self._project = project
        self._folder = folder
        self._item_names = item_names
        self._annotation_status_code = annotation_status
        self._service_provider = service_provider

    def validate_items(self):
        if not self._item_names:
            self._item_names = [
                item.name
                for item in self._service_provider.item_service.list(
                    self._project.id, self._folder.id, EmptyQuery()
                )
            ]
            return
        existing_items = []
        for i in range(0, len(self._item_names), self.CHUNK_SIZE):
            search_names = self._item_names[i : i + self.CHUNK_SIZE]  # noqa
            data = self._service_provider.item_service.list(
                self._project.id,
                self._folder.id,
                Filter("name", search_names, OperatorEnum.IN),
            )
            existing_items += data
        if not existing_items:
            raise AppValidationException(self.ERROR_MESSAGE)
        if existing_items:
            self._item_names = list(
                {i.name for i in existing_items}.intersection(set(self._item_names))
            )

    def execute(self):
        if self.is_valid():
            for i in range(0, len(self._item_names), self.CHUNK_SIZE):
                status_changed = self._service_provider.items.set_statuses(
                    project=self._project,
                    folder=self._folder,
                    item_names=self._item_names[i : i + self.CHUNK_SIZE],  # noqa: E203,
                    annotation_status=self._annotation_status_code,
                )
                if not status_changed:
                    self._response.errors = AppException(self.ERROR_MESSAGE)
                    break
        return self._response


class SetApprovalStatues(BaseReportableUseCase):
    CHUNK_SIZE = 3000
    ERROR_MESSAGE = "Failed to change approval status."

    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        folder: FolderEntity,
        approval_status: str,
        service_provider: BaseServiceProvider,
        item_names: List[str] = None,
    ):
        super().__init__(reporter)
        self._project = project
        self._folder = folder
        self._item_names = item_names
        self._approval_status_code = constants.ApprovalStatus(approval_status).value
        self._service_provider = service_provider

    def validate_items(self):
        if not self._item_names:
            self._item_names = self._item_names = [
                item.name
                for item in self._service_provider.item_service.list(
                    self._project.id, self._folder.id, EmptyQuery()
                )
            ]
        else:
            _tmp = set(self._item_names)
            unique, total = len(_tmp), len(self._item_names)
            if unique < total:
                logger.info(
                    f"Dropping duplicates. Found {unique}/{total} unique items."
                )
            self._item_names = list(_tmp)
            existing_items = []
            for i in range(0, len(self._item_names), self.CHUNK_SIZE):
                search_names = self._item_names[i : i + self.CHUNK_SIZE]  # noqa
                data = self._service_provider.item_service.list(
                    self._project.id,
                    self._folder.id,
                    Filter("name", search_names, OperatorEnum.IN),
                )
                cand_items = data
                existing_items += cand_items
            if not existing_items:
                raise AppValidationException("No items found.")
            if existing_items:
                self._item_names = list(
                    {i.name for i in existing_items}.intersection(set(self._item_names))
                )

    def execute(self):
        if self.is_valid():
            total_items = 0
            for i in range(0, len(self._item_names), self.CHUNK_SIZE):
                response = self._service_provider.items.set_approval_statuses(
                    project=self._project,
                    folder=self._folder,
                    item_names=self._item_names[i : i + self.CHUNK_SIZE],  # noqa: E203,
                    approval_status=self._approval_status_code,
                )
                if not response.ok:
                    if response.error == "Unsupported project type.":
                        self._response.errors = (
                            f"The function is not supported for"
                            f" {constants.ProjectType(self._project.type).name} projects."
                        )
                    else:
                        self._response.errors = self.ERROR_MESSAGE
                    return self._response
                total_items += len(response.data)
            if total_items:
                logger.info(
                    f"Successfully updated {total_items}/{len(self._item_names)} item(s)"
                )
        return self._response


class DeleteItemsUseCase(BaseUseCase):
    CHUNK_SIZE = 1000

    def __init__(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        service_provider: BaseServiceProvider,
        item_names: List[str] = None,
    ):
        super().__init__()
        self._project = project
        self._folder = folder
        self._service_provider = service_provider
        self._item_names = item_names

    def execute(self):
        if self.is_valid():
            if self._item_names:
                item_ids = []
                for chunk in divide_to_chunks(self._item_names, 500):
                    data = self._service_provider.item_service.list(
                        self._project.id,
                        self._folder.id,
                        Filter("name", chunk, OperatorEnum.IN),
                    )
                    item_ids.extend([i.id for i in data])
            else:
                items = self._service_provider.item_service.list(
                    self._project.id, self._folder.id, EmptyQuery()
                )
                item_ids = [item.id for item in items]

            for i in range(0, len(item_ids), self.CHUNK_SIZE):
                self._service_provider.items.delete_multiple(
                    project=self._project,
                    item_ids=item_ids[i : i + self.CHUNK_SIZE],  # noqa: E203
                )
            logger.info(
                f"Items deleted in project {self._project.name}{'/' + self._folder.name if not self._folder.is_root else ''}"
            )

        return self._response


class AddItemsToSubsetUseCase(BaseUseCase):
    CHUNK_SIZE = 5000

    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        subset_name: str,
        items: List[dict],
        service_provider: BaseServiceProvider,
        root_folder: FolderEntity,
    ):
        self.reporter = reporter
        self.project = project
        self.subset_name = subset_name
        self.items = items
        self._provided_item_count = len(items)
        self.results = {"succeeded": [], "failed": [], "skipped": []}
        self.item_ids = []
        self.path_separated = defaultdict(dict)
        self._service_provider = service_provider
        self.root_folder = root_folder
        super().__init__()

    def __filter_duplicates(
        self,
    ):
        def uniqueQ(item, seen):
            result = True
            if "id" in item:
                if item["id"] in seen:
                    result = False
                else:
                    seen.add(item["id"])
            if "name" in item and "path" in item:
                unique_str = f"{item['path']}/{item['name']}"
                if unique_str in seen:
                    result = False
                else:
                    seen.add(unique_str)
            return result

        seen = set()
        uniques = [x for x in self.items if uniqueQ(x, seen)]
        return uniques

    def __filter_invalid_items(
        self,
    ):
        def validQ(item):
            if "id" in item:
                return True
            if "name" in item and "path" in item:
                return True
            self.results["skipped"].append(item)
            return False

        filtered_items = [x for x in self.items if validQ(x)]

        return filtered_items

    def __separate_to_paths(
        self,
    ):
        for item in self.items:
            if "id" in item:
                self.item_ids.append(item["id"])
            else:
                if "items" not in self.path_separated[item["path"]]:
                    self.path_separated[item["path"]]["items"] = []

                self.path_separated[item["path"]]["items"].append(item)

        # Removing paths that have incorrect folders in them
        # And adding their items to "skipped list" and removing it from self.path_separated
        # so that we don't query them later.
        # Otherwise include folder in path object in order to later run a query

        removables = []
        for path, value in self.path_separated.items():

            project, folder = extract_project_folder(path)

            if project != self.project.name:
                removables.append(path)
                continue

            # If no folder was provided in the path use "root"
            # Problems with folders name 'root' are going to arise

            if not folder:
                value["folder"] = self.root_folder
                continue
            condition = Condition("name", folder, EQ)
            folder_found = False
            try:
                folder_candidates = SearchFoldersUseCase(
                    project=self.project,
                    service_provider=self._service_provider,
                    condition=condition,
                ).execute()
                if folder_candidates.errors:
                    raise AppException(folder_candidates.errors)
                for f in folder_candidates.data:
                    if f.name == folder:
                        value["folder"] = f
                        folder_found = True
                        break
                # If the folder did not exist add to skipped
                if not folder_found:
                    removables.append(path)

            except Exception as _:
                removables.append(path)

        # Removing completely incorrect paths and their items
        for item in removables:
            self.results["skipped"].extend(self.path_separated[item]["items"])
            self.path_separated.pop(item)

    def __build_query_string(self, path, item_names):
        _, folder = extract_project_folder(path)
        if not folder:
            folder = "root"
        query_str = f"metadata(name IN {str(item_names)}) AND folderName={folder}"

        return query_str

    def __query(self, path, items):
        _, __ = extract_project_folder(path)

        item_names = [item["name"] for item in items["items"]]
        query = self.__build_query_string(path, item_names)
        query_use_case = QueryEntitiesUseCase(
            reporter=self.reporter,
            project=self.project,
            service_provider=self._service_provider,
            query=query,
            folder=items["folder"],
            subset=None,
        )

        queried_items = query_use_case.execute()
        # If we failed the query for whatever reason
        # Add all items of the folder to skipped
        if queried_items.errors:
            self.results["skipped"].extend(items["items"])
            return

        queried_items = queried_items.data
        # Adding the images missing from specified folder to 'skipped'
        tmp = {item["name"]: item for item in items["items"]}
        tmp_q = {x["name"] for x in queried_items}

        for i, val in tmp.items():
            if i not in tmp_q:
                self.results["skipped"].append(val)

        # Adding ids to path_separated to later see if they've succeded

        self.path_separated[path] = [
            {"id": x["id"], "name": x["name"], "path": x["path"]} for x in queried_items
        ]
        return [x["id"] for x in queried_items]

    def __distribute_to_results(self, item_id, response, item):

        if item_id in response.data["success"]:
            self.results["succeeded"].append(item)
            response.data["success"].discard(item_id)
        elif item_id in response.data["skipped"]:
            self.results["skipped"].append(item)
            response.data["skipped"].discard(item_id)
        elif item_id in response.data["failed"]:
            self.results["failed"].append(item)
            response.data["failed"].discard(item_id)

    def validate_items(
        self,
    ):

        filtered_items = self.__filter_duplicates()
        self.items = filtered_items
        self.items = self.__filter_invalid_items()
        self.__separate_to_paths()

    def validate_project(self):
        response = self._service_provider.explore.validate_saqul_query(
            self.project, "_"
        )
        if not response.ok:
            raise AppException(response.error)

    def execute(
        self,
    ):
        if self.is_valid():
            futures = []
            with ThreadPoolExecutor(max_workers=4) as executor:
                for path, items in self.path_separated.items():
                    future = executor.submit(self.__query, path, items)
                    futures.append(future)

            for future in as_completed(futures):
                try:
                    ids = future.result()
                    self.item_ids.extend(ids)
                except Exception:
                    logger.debug(traceback.format_exc())
                    raise

            subsets = self._service_provider.explore.list_subsets(self.project).data
            subset = None
            for s in subsets:
                if s.name == self.subset_name:
                    subset = s
                    break

            if not subset:
                subset = self._service_provider.explore.create_multiple_subsets(
                    self.project, [self.subset_name]
                ).data[0]

                self.reporter.log_info(
                    f"You've successfully created a new subset - {self.subset_name}."
                )

            response = None

            unique_item_ids = list(set(self.item_ids))
            processed_items = len(unique_item_ids) + len(self.results["skipped"])
            if self._provided_item_count > processed_items:
                self.reporter.log_info(
                    f"Dropping duplicates. Found {processed_items} / {self._provided_item_count} unique items."
                )
            for i in range(0, len(unique_item_ids), self.CHUNK_SIZE):
                tmp_response = self._service_provider.explore.add_items_to_subset(
                    project=self.project,
                    item_ids=unique_item_ids[i : i + self.CHUNK_SIZE],  # noqa
                    subset=subset,
                )

                if not response:
                    response = tmp_response
                else:
                    response.data["failed"] = response.data["failed"].union(
                        tmp_response.data["failed"]
                    )
                    response.data["skipped"] = response.data["skipped"].union(
                        tmp_response.data["skipped"]
                    )
                    response.data["success"] = response.data["success"].union(
                        tmp_response.data["success"]
                    )

            # Iterating over all path_separated (that now have ids in them and sorting them into
            # "success", "failed" and "skipped")

            for path, value in self.path_separated.items():
                for item in value:
                    item_id = item.pop(
                        "id", None
                    )  # Need to remove it, since its added artificially
                    self.__distribute_to_results(item_id, response, item)

            for item in self.items:
                if "id" not in item:
                    continue
                item_id = item[
                    "id"
                ]  # No need to remove id, since it was supplied by the user

                self.__distribute_to_results(item_id, response, item)

            self._response.data = self.results
            # The function should either return something or raise an exception prior to
            # returning control to the interface function that called it. So no need for
            # error handling in the response
            return self._response
