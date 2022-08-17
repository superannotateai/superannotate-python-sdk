import asyncio
import concurrent.futures
import copy
import io
import json
import os
import platform
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from itertools import islice
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple

import boto3
import jsonschema.validators
import lib.core as constants
import nest_asyncio
from jsonschema import Draft7Validator
from jsonschema import ValidationError
from lib.core.conditions import Condition
from lib.core.conditions import CONDITION_EQ as EQ
from lib.core.entities import AnnotationClassEntity
from lib.core.entities import FolderEntity
from lib.core.entities import ImageEntity
from lib.core.entities import ProjectEntity
from lib.core.entities import TeamEntity
from lib.core.exceptions import AppException
from lib.core.reporter import Reporter
from lib.core.repositories import BaseManageableRepository
from lib.core.repositories import BaseReadOnlyRepository
from lib.core.response import Response
from lib.core.service_types import UploadAnnotationAuthData
from lib.core.serviceproviders import SuperannotateServiceProvider
from lib.core.types import PriorityScore
from lib.core.usecases.base import BaseReportableUseCase
from lib.core.usecases.images import GetBulkImages
from lib.core.video_convertor import VideoFrameGenerator
from superannotate.logger import get_default_logger

logger = get_default_logger()

if platform.system().lower() == "windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

BIG_FILE_THRESHOLD = 15 * 1024 * 1024

nest_asyncio.apply()


@dataclass
class Report:
    failed_annotations: list
    missing_classes: list
    missing_attr_groups: list
    missing_attrs: list


class UploadAnnotationsUseCase(BaseReportableUseCase):
    MAX_WORKERS = 16
    CHUNK_SIZE = 100
    CHUNK_SIZE_MB = 10 * 1024 * 1024
    STATUS_CHANGE_CHUNK_SIZE = 100
    AUTH_DATA_CHUNK_SIZE = 500
    THREADS_COUNT = 4
    URI_THRESHOLD = 4 * 1024 - 120

    @dataclass
    class AnnotationToUpload:
        id: int
        name: str
        path: str
        data: io.StringIO = None
        mask: io.BytesIO = None

    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        folder: FolderEntity,
        team: TeamEntity,
        images: BaseManageableRepository,
        folders: BaseManageableRepository,
        annotation_classes: List[AnnotationClassEntity],
        annotation_paths: List[str],
        backend_service_provider: SuperannotateServiceProvider,
        templates: List[dict],
        pre_annotation: bool = False,
        client_s3_bucket=None,
        folder_path: str = None,
    ):
        super().__init__(reporter)
        self._project = project
        self._folder = folder
        self._team = team
        self._images = images
        self._folders = folders
        self._backend_service = backend_service_provider
        self._annotation_classes = annotation_classes
        self._annotation_paths = annotation_paths
        self._client_s3_bucket = client_s3_bucket
        self._pre_annotation = pre_annotation
        self._templates = templates
        self._annotations_to_upload = []
        self._missing_annotations = []
        self.missing_attribute_groups = set()
        self.missing_classes = set()
        self.missing_attributes = set()
        self._folder_path = folder_path
        if "classes/classes.json" in self._annotation_paths:
            self._annotation_paths.remove("classes/classes.json")
        self._annotation_upload_data = None
        self._item_ids = []
        self._s3_bucket = None
        self._big_files_queue = asyncio.Queue()
        self._small_files_queue = asyncio.Queue()
        self._report = Report([], [], [], [])

    @staticmethod
    def get_name_path_mappings(annotation_paths):
        name_path_mappings: Dict[str, str] = {}

        for item_path in annotation_paths:
            name_path_mappings[
                UploadAnnotationsUseCase.extract_name(Path(item_path).name)
            ] = item_path
        return name_path_mappings

    def _log_report(
        self,
    ):
        if self._report.missing_classes:
            logger.warning(
                "Could not find annotation classes matching existing classes on the platform: "
                f"[{', '.join(self._report.missing_classes)}]"
            )
        if self._report.missing_attr_groups:
            logger.warning(
                "Could not find attribute groups matching existing attribute groups on the platform: "
                f"[{', '.join(self._report.missing_attr_groups)}]"
            )
        if self._report.missing_attrs:
            logger.warning(
                "Could not find attributes matching existing attributes on the platform: "
                f"[{', '.join(self._report.missing_attrs)}]"
            )

        if self.reporter.custom_messages.get("invalid_jsons"):
            logger.warning(
                f"Couldn't validate {len(self.reporter.custom_messages['invalid_jsons'])}/"
                f"{len(self._annotation_paths)} annotations from {self._folder_path}. "
                f"{constants.USE_VALIDATE_MESSAGE}"
            )

    @staticmethod
    def get_annotation_from_s3(bucket, path: str):
        session = boto3.Session().resource("s3")
        file = io.BytesIO()
        s3_object = session.Object(bucket, path)
        s3_object.download_fileobj(file)
        file.seek(0)
        return file

    def prepare_annotation(self, annotation: dict) -> dict:
        errors = None
        if sys.getsizeof(annotation) < BIG_FILE_THRESHOLD:
            use_case = ValidateAnnotationUseCase(
                reporter=self.reporter,
                team_id=self._project.team_id,
                project_type=self._project.type,
                annotation=annotation,
                backend_service_provider=self._backend_service,
            )
            errors = use_case.execute().data
        if errors:
            raise AppException(errors)

        annotation = UploadAnnotationUseCase.set_defaults(
            self._team.creator_id, annotation, self._project.type
        )
        return annotation

    def get_annotation(
        self, path: str
    ) -> (Optional[Tuple[io.StringIO]], Optional[io.BytesIO]):
        mask = None
        if self._client_s3_bucket:
            annotation = json.load(
                self.get_annotation_from_s3(self._client_s3_bucket, path)
            )
        else:
            annotation = json.load(open(path))
            if self._project.type == constants.ProjectType.PIXEL.value:
                mask = open(
                    path.replace(
                        constants.PIXEL_ANNOTATION_POSTFIX,
                        constants.ANNOTATION_MASK_POSTFIX,
                    ),
                    "rb",
                )
        annotation = self.prepare_annotation(annotation)
        if not annotation:
            self.reporter.store_message("invalid_jsons", path)
            return None, None
        return annotation, mask

    @staticmethod
    def chunks(data, size: int = 10000):
        it = iter(data)
        for i in range(0, len(data), size):
            yield {k: data[k] for k in islice(it, size)}

    @staticmethod
    def extract_name(value: str):
        return os.path.basename(
            value.replace(constants.PIXEL_ANNOTATION_POSTFIX, "")
            .replace(constants.VECTOR_ANNOTATION_POSTFIX, "")
            .replace(constants.ATTACHED_VIDEO_ANNOTATION_POSTFIX, ""),
        )

    def get_existing_name_item_mapping(
        self, name_path_mappings: Dict[str, str]
    ) -> dict:
        item_names = list(name_path_mappings.keys())
        existing_name_item_mapping = {}
        for i in range(0, len(item_names), self.CHUNK_SIZE):
            items_to_check = item_names[i : i + self.CHUNK_SIZE]  # noqa: E203
            response = GetBulkImages(
                service=self._backend_service,
                project_id=self._project.id,
                team_id=self._project.team_id,
                folder_id=self._folder.uuid,
                images=items_to_check,
            ).execute()
            if not response.errors:
                existing_name_item_mapping.update({i.name: i for i in response.data})
        return existing_name_item_mapping

    def _set_annotation_statuses_in_progress(self, item_names: List[str]) -> bool:
        failed_on_chunk = False
        for i in range(0, len(item_names), self.STATUS_CHANGE_CHUNK_SIZE):
            status_changed = self._backend_service.set_images_statuses_bulk(
                image_names=item_names[i : i + self.CHUNK_SIZE],  # noqa: E203
                team_id=self._project.team_id,
                project_id=self._project.id,
                folder_id=self._folder.uuid,
                annotation_status=constants.AnnotationStatus.IN_PROGRESS.value,
            )
            if not status_changed:
                failed_on_chunk = True
        return not failed_on_chunk

    @property
    def annotation_upload_data(self) -> UploadAnnotationAuthData:
        if not self._annotation_upload_data:
            response = self._backend_service.get_annotation_upload_data(
                project_id=self._project.id,
                team_id=self._project.team_id,
                folder_id=self._folder.uuid,
                image_ids=self._item_ids,
            )
            if response.ok:
                self._annotation_upload_data = response.data
        return self._annotation_upload_data

    @property
    def s3_bucket(self):
        if not self._s3_bucket:
            upload_data = self.annotation_upload_data
            if upload_data:
                session = boto3.Session(
                    aws_access_key_id=upload_data.access_key,
                    aws_secret_access_key=upload_data.secret_key,
                    aws_session_token=upload_data.session_token,
                    region_name=upload_data.region,
                )
                resource = session.resource("s3")
                self._s3_bucket = resource.Bucket(upload_data.bucket)
        return self._s3_bucket

    def _upload_mask(self, item: AnnotationToUpload):
        self.s3_bucket.put_object(
            Key=self.annotation_upload_data.images[item.id]["annotation_bluemap_path"],
            Body=item.mask,
        )

    async def _upload_small_annotations(self, chunk) -> Report:
        failed_annotations, missing_classes, missing_attr_groups, missing_attrs = (
            [],
            [],
            [],
            [],
        )
        response = await self._backend_service.upload_annotations(
            team_id=self._project.team_id,
            project_id=self._project.id,
            folder_id=self._folder.id,
            items_name_file_map={i.name: i.data for i in chunk},
        )
        self.reporter.update_progress(len(chunk))
        if response.ok:
            if response.data.failed_items:  # noqa
                failed_annotations = response.data.failed_items
            missing_classes = response.data.missing_resources.classes
            missing_attr_groups = response.data.missing_resources.attribute_groups
            missing_attrs = response.data.missing_resources.attributes
            if self._project.type == constants.ProjectType.PIXEL.value:
                for i in chunk:
                    if i.mask:
                        self._upload_mask(i)
        else:
            failed_annotations.extend([i.name for i in chunk])
        return Report(
            failed_annotations, missing_classes, missing_attr_groups, missing_attrs
        )

    async def upload_small_annotations(self):
        chunk = []

        async def upload(_chunk):
            try:
                report = await self._upload_small_annotations(chunk)
                self._report.failed_annotations.extend(report.failed_annotations)
                self._report.missing_classes.extend(report.missing_classes)
                self._report.missing_attr_groups.extend(report.missing_attr_groups)
                self._report.missing_attrs.extend(report.missing_attrs)
            except Exception:
                import traceback

                traceback.print_exc()
                self._report.failed_annotations.extend([i.name for i in chunk])

        while True:
            item = await self._small_files_queue.get()
            self._small_files_queue.task_done()
            if not item:
                self._small_files_queue.put_nowait(None)
                break
            chunk.append(item)
            if (
                sys.getsizeof(chunk) >= self.CHUNK_SIZE_MB
                or sum([len(i.name) for i in chunk])
                >= self.URI_THRESHOLD - len(chunk) * 14
            ):
                await upload(chunk)
                chunk = []

        if chunk:
            await upload(chunk)

    async def _upload_big_annotation(self, item) -> Tuple[str, bool]:
        try:
            is_uploaded = await self._backend_service.upload_big_annotation(
                team_id=self._project.team_id,
                project_id=self._project.id,
                folder_id=self._folder.uuid,
                item_id=item.id,
                data=item.data,
                chunk_size=5 * 1024 * 1024,
            )
            self.reporter.update_progress()
            if is_uploaded and (
                self._project.type == constants.ProjectType.PIXEL.value and item.mask
            ):
                self._upload_mask(item.mask)
            return item.name, is_uploaded
        except AppException as e:
            self.reporter.log_error(str(e))
            self._report.failed_annotations.append(item.name)

    async def upload_big_annotations(self):
        while True:
            item = await self._big_files_queue.get()
            self._big_files_queue.task_done()
            if not item:
                self._big_files_queue.put_nowait(None)
                return
            await self._upload_big_annotation(item)

    async def distribute_queues(self, items_to_upload: list):
        data: List[List[Any, bool]] = [[i, False] for i in items_to_upload]
        processed_count = 0
        while processed_count < len(data):
            for idx, (item, processed) in enumerate(data):
                if not processed:
                    try:
                        annotation, mask = self.get_annotation(item.path)
                        t_item = copy.copy(item)
                        size = sys.getsizeof(annotation)
                        annotation_file = io.StringIO()
                        json.dump(annotation, annotation_file)
                        annotation_file.seek(0)
                        t_item.data = annotation_file
                        t_item.mask = mask
                        if size > BIG_FILE_THRESHOLD:
                            if self._big_files_queue.qsize() > 4:
                                continue
                            else:
                                self._big_files_queue.put_nowait(t_item)
                        else:
                            self._small_files_queue.put_nowait(t_item)
                    except (ValidationError, AppException):
                        self._report.failed_annotations.append(item.name)
                    finally:
                        data[idx][1] = True
                        processed_count += 1
        self._big_files_queue.put_nowait(None)
        self._small_files_queue.put_nowait(None)

    async def run_workers(self, items_to_upload):
        try:
            await asyncio.gather(
                self.distribute_queues(items_to_upload),
                self.upload_small_annotations(),
                self.upload_big_annotations(),
                self.upload_big_annotations(),
                self.upload_big_annotations(),
                self.upload_big_annotations(),
                return_exceptions=True,
            )
        except Exception as e:
            self.reporter.log_error(f"Error {str(e)}")

    def execute(self):
        missing_annotations = []
        self.reporter.start_progress(
            len(self._annotation_paths), description="Uploading Annotations"
        )
        name_path_mappings = self.get_name_path_mappings(self._annotation_paths)
        existing_name_item_mapping = self.get_existing_name_item_mapping(
            name_path_mappings
        )
        name_path_mappings_to_upload = {}
        items_to_upload = []

        for name, path in name_path_mappings.items():
            try:
                item = existing_name_item_mapping.pop(name)
                name_path_mappings_to_upload[name] = path
                self._item_ids.append(item.uuid)
                items_to_upload.append(self.AnnotationToUpload(item.uuid, name, path))
            except KeyError:
                missing_annotations.append(name)

        asyncio.run(self.run_workers(items_to_upload))
        self.reporter.finish_progress()
        self._log_report()
        uploaded_annotations = list(
            name_path_mappings.keys()
            - set(self._report.failed_annotations).union(set(missing_annotations))
        )
        if uploaded_annotations:
            statuses_changed = self._set_annotation_statuses_in_progress(
                uploaded_annotations
            )
            if not statuses_changed:
                self._response.errors = AppException("Failed to change status.")

        if self._report.failed_annotations:
            self.reporter.log_warning(
                f"Couldn't validate annotations. {constants.USE_VALIDATE_MESSAGE}"
            )
        self._response.data = (
            uploaded_annotations,
            self._report.failed_annotations,
            missing_annotations,
        )
        return self._response


class UploadAnnotationUseCase(BaseReportableUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        image: ImageEntity,
        images: BaseManageableRepository,
        team: TeamEntity,
        annotation_classes: List[AnnotationClassEntity],
        backend_service_provider: SuperannotateServiceProvider,
        reporter: Reporter,
        templates: List[dict],
        annotation_upload_data: UploadAnnotationAuthData = None,
        annotations: dict = None,
        s3_bucket=None,
        client_s3_bucket=None,
        mask=None,
        verbose: bool = True,
        annotation_path: str = None,
        pass_validation: bool = False,
    ):
        super().__init__(reporter)
        self._project = project
        self._folder = folder
        self._image = image
        self._images = images
        self._team = team
        self._backend_service = backend_service_provider
        self._annotation_classes = annotation_classes
        self._annotation_json = annotations
        self._mask = mask
        self._verbose = verbose
        self._templates = templates
        self._annotation_path = annotation_path
        self._annotation_upload_data = annotation_upload_data
        self._s3_bucket = s3_bucket
        self._client_s3_bucket = client_s3_bucket
        self._pass_validation = pass_validation

    @property
    def annotation_upload_data(self) -> UploadAnnotationAuthData:
        if not self._annotation_upload_data:
            response = self._backend_service.get_annotation_upload_data(
                project_id=self._project.id,
                team_id=self._project.team_id,
                folder_id=self._folder.uuid,
                image_ids=[self._image.uuid],
            )
            if response.ok:
                self._annotation_upload_data = response.data
        return self._annotation_upload_data

    @property
    def s3_bucket(self):
        if not self._s3_bucket:
            upload_data = self.annotation_upload_data
            if upload_data:
                session = boto3.Session(
                    aws_access_key_id=upload_data.access_key,
                    aws_secret_access_key=upload_data.secret_key,
                    aws_session_token=upload_data.session_token,
                    region_name=upload_data.region,
                )
                resource = session.resource("s3")
                self._s3_bucket = resource.Bucket(upload_data.bucket)
        return self._s3_bucket

    def get_s3_file(self, s3, path: str):
        file = io.BytesIO()
        s3_object = s3.Object(self._client_s3_bucket, path)
        s3_object.download_fileobj(file)
        file.seek(0)
        return file

    @property
    def from_s3(self):
        if self._client_s3_bucket:
            from_session = boto3.Session()
            return from_session.resource("s3")

    def _get_annotation_json(self) -> tuple:
        annotation_json, mask = None, None
        if not self._annotation_json:
            if self._client_s3_bucket:
                annotation_json = json.load(
                    self.get_s3_file(self.from_s3, self._annotation_path)
                )
                if self._project.type == constants.ProjectType.PIXEL.value:
                    self._mask = self.get_s3_file(
                        self.from_s3,
                        self._annotation_path.replace(
                            constants.PIXEL_ANNOTATION_POSTFIX,
                            constants.ANNOTATION_MASK_POSTFIX,
                        ),
                    )
            else:
                annotation_json = json.load(open(self._annotation_path))
                if self._project.type == constants.ProjectType.PIXEL.value:
                    mask = open(
                        self._annotation_path.replace(
                            constants.PIXEL_ANNOTATION_POSTFIX,
                            constants.ANNOTATION_MASK_POSTFIX,
                        ),
                        "rb",
                    )
        else:
            return self._annotation_json, self._mask
        return annotation_json, mask

    def _validate_json(self, json_data: dict) -> list:
        use_case = ValidateAnnotationUseCase(
            reporter=self.reporter,
            team_id=self._project.team_id,
            project_type=self._project.type,
            annotation=json_data,
            backend_service_provider=self._backend_service,
        )
        return use_case.execute().data

    @staticmethod
    def set_defaults(team_id, annotation_data: dict, project_type: int):
        default_data = {}
        annotation_data["metadata"]["lastAction"] = {
            "email": team_id,
            "timestamp": int(round(time.time() * 1000)),
        }
        instances = annotation_data.get("instances", [])
        if project_type in constants.ProjectType.images:
            default_data["probability"] = 100

        if project_type == constants.ProjectType.VIDEO.value:
            for instance in instances:
                instance["meta"] = {
                    **default_data,
                    **instance["meta"],
                    "creationType": "Preannotation",  # noqa
                }
        else:
            for idx, instance in enumerate(instances):
                instances[idx] = {
                    **default_data,
                    **instance,
                    "creationType": "Preannotation",  # noqa
                }
        return annotation_data

    def execute(self):
        if self.is_valid():
            annotation_json, mask = self._get_annotation_json()
            errors = self._validate_json(annotation_json)
            annotation_json = UploadAnnotationUseCase.set_defaults(
                self._team.creator_id, annotation_json, self._project.type
            )
            if not errors:
                annotation_file = io.StringIO()
                json.dump(annotation_json, annotation_file)
                size = annotation_file.tell()
                annotation_file.seek(0)
                if size > BIG_FILE_THRESHOLD:
                    uploaded = asyncio.run(
                        self._backend_service.upload_big_annotation(
                            team_id=self._project.team_id,
                            project_id=self._project.id,
                            folder_id=self._folder.uuid,
                            item_id=self._image.id,
                            data=annotation_file,
                            chunk_size=5 * 1024 * 1024,
                        )
                    )
                    if not uploaded:
                        self._response.errors = constants.INVALID_JSON_MESSAGE

                else:
                    response = asyncio.run(
                        self._backend_service.upload_annotations(
                            team_id=self._project.team_id,
                            project_id=self._project.id,
                            folder_id=self._folder.uuid,
                            items_name_file_map={self._image.name: annotation_file},
                        )
                    )
                    if response.ok:
                        missing_classes = response.data.missing_resources.classes
                        missing_attr_groups = (
                            response.data.missing_resources.attribute_groups
                        )
                        missing_attrs = response.data.missing_resources.attributes
                        for class_name in missing_classes:
                            self.reporter.log_warning(
                                f"Couldn't find class {class_name}."
                            )
                        for attr_group in missing_attr_groups:
                            self.reporter.log_warning(
                                f"Couldn't find annotation group {attr_group}."
                            )
                        for attr in missing_attrs:
                            self.reporter.log_warning(
                                f"Couldn't find attribute {attr}."
                            )

                        if (
                            self._project.type == constants.ProjectType.PIXEL.value
                            and mask
                        ):
                            self.s3_bucket.put_object(
                                Key=self.annotation_upload_data.images[
                                    self._image.uuid
                                ]["annotation_bluemap_path"],
                                Body=mask,
                            )
                    self._image.annotation_status_code = (
                        constants.AnnotationStatus.IN_PROGRESS.value
                    )
                    self._images.update(self._image)
                    if self._verbose:
                        self.reporter.log_info(
                            f"Uploading annotations for image {str(self._image.name)} in project {self._project.name}."
                        )
            else:
                self._response.errors = constants.INVALID_JSON_MESSAGE
                self.reporter.store_message("invalid_jsons", self._annotation_path)
                self.reporter.log_warning(
                    f"Couldn't validate annotations. {constants.USE_VALIDATE_MESSAGE}"
                )
        return self._response


class GetAnnotations(BaseReportableUseCase):
    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        folder: FolderEntity,
        images: BaseManageableRepository,
        item_names: Optional[List[str]],
        backend_service_provider: SuperannotateServiceProvider,
        show_process: bool = True,
    ):
        super().__init__(reporter)
        self._project = project
        self._folder = folder
        self._images = images
        self._item_names = item_names
        self._client = backend_service_provider
        self._show_process = show_process
        self._item_names_provided = True

    def validate_project_type(self):
        if self._project.type == constants.ProjectType.PIXEL.value:
            raise AppException("The function is not supported for Pixel projects.")

    def validate_item_names(self):
        if self._item_names:
            item_names = list(dict.fromkeys(self._item_names))
            len_unique_items, len_items = len(item_names), len(self._item_names)
            if len_unique_items < len_items:
                self.reporter.log_info(
                    f"Dropping duplicates. Found {len_unique_items}/{len_items} unique items."
                )
                self._item_names = item_names
        else:
            self._item_names_provided = False
            condition = (
                Condition("team_id", self._project.team_id, EQ)
                & Condition("project_id", self._project.id, EQ)
                & Condition("folder_id", self._folder.uuid, EQ)
            )

            self._item_names = [item.name for item in self._images.get_all(condition)]

    def _prettify_annotations(self, annotations: List[dict]):
        if self._item_names_provided:
            try:
                data = []
                for annotation in annotations:
                    data.append(
                        (
                            self._item_names.index(annotation["metadata"]["name"]),
                            annotation,
                        )
                    )
                return [i[1] for i in sorted(data, key=lambda x: x[0])]
            except KeyError:
                raise AppException("Broken data.")
        return annotations

    def execute(self):
        if self.is_valid():
            items_count = len(self._item_names)
            self.reporter.log_info(
                f"Getting {items_count} annotations from "
                f"{self._project.name}{f'/{self._folder.name}' if self._folder.name != 'root' else ''}."
            )
            self.reporter.start_progress(items_count, disable=not self._show_process)
            annotations = self._client.get_annotations(
                team_id=self._project.team_id,
                project_id=self._project.id,
                folder_id=self._folder.uuid,
                items=self._item_names,
                reporter=self.reporter,
            )
            received_items_count = len(annotations)
            self.reporter.finish_progress()
            if items_count > received_items_count:
                self.reporter.log_warning(
                    f"Could not find annotations for {items_count - received_items_count}/{items_count} items."
                )
            self._response.data = self._prettify_annotations(annotations)
        return self._response


class GetVideoAnnotationsPerFrame(BaseReportableUseCase):
    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        folder: FolderEntity,
        images: BaseManageableRepository,
        video_name: str,
        fps: int,
        backend_service_provider: SuperannotateServiceProvider,
    ):
        super().__init__(reporter)
        self._project = project
        self._folder = folder
        self._images = images
        self._video_name = video_name
        self._fps = fps
        self._client = backend_service_provider

    def validate_project_type(self):
        if self._project.type != constants.ProjectType.VIDEO.value:
            raise AppException(
                "The function is not supported for"
                f" {constants.ProjectType.get_name(self._project.type)} projects."
            )

    def execute(self):
        if self.is_valid():
            self.reporter.disable_info()
            response = GetAnnotations(
                reporter=self.reporter,
                project=self._project,
                folder=self._folder,
                images=self._images,
                item_names=[self._video_name],
                backend_service_provider=self._client,
                show_process=False,
            ).execute()
            self.reporter.enable_info()
            if response.data:
                generator = VideoFrameGenerator(response.data[0], fps=self._fps)
                self.reporter.log_info(
                    f"Getting annotations for {generator.frames_count} frames from {self._video_name}."
                )
                if response.errors:
                    self._response.errors = response.errors
                    return self._response
                if not response.data:
                    self._response.errors = AppException(
                        f"Video {self._video_name} not found."
                    )
                annotations = response.data
                if annotations:
                    self._response.data = list(generator)
                else:
                    self._response.data = []
            else:
                self._response.errors = "Couldn't get annotations."
        return self._response


class UploadPriorityScoresUseCase(BaseReportableUseCase):
    CHUNK_SIZE = 100

    def __init__(
        self,
        reporter,
        project: ProjectEntity,
        folder: FolderEntity,
        scores: List[PriorityScore],
        project_folder_name: str,
        backend_service_provider: SuperannotateServiceProvider,
    ):
        super().__init__(reporter)
        self._project = project
        self._folder = folder
        self._scores = scores
        self._client = backend_service_provider
        self._project_folder_name = project_folder_name

    @staticmethod
    def get_clean_priority(priority):
        if len(str(priority)) > 8:
            priority = float(str(priority)[:8])
        if priority > 1000000:
            priority = 1000000
        if priority < 0:
            priority = 0
        if str(float(priority)).split(".")[1:2]:
            if len(str(float(priority)).split(".")[1]) > 5:
                priority = float(
                    str(float(priority)).split(".")[0]
                    + "."
                    + str(float(priority)).split(".")[1][:5]
                )
        return priority

    @property
    def folder_path(self):
        return f"{self._project.name}{f'/{self._folder.name}' if self._folder.name != 'root' else ''}"

    @property
    def uploading_info(self):
        data_len: int = len(self._scores)
        return (
            f"Uploading  priority scores for {data_len} item(s) to {self.folder_path}."
        )

    def execute(self):
        if self.is_valid():
            priorities = []
            initial_scores = []
            for i in self._scores:
                priorities.append(
                    {
                        "name": i.name,
                        "entropy_value": self.get_clean_priority(i.priority),
                    }
                )
                initial_scores.append(i.name)
            uploaded_score_names = []
            self.reporter.log_info(self.uploading_info)
            iterations = range(0, len(priorities), self.CHUNK_SIZE)
            self.reporter.start_progress(iterations, "Uploading priority scores")
            if iterations:
                for i in iterations:
                    priorities_to_upload = priorities[
                        i : i + self.CHUNK_SIZE
                    ]  # noqa: E203
                    res = self._client.upload_priority_scores(
                        team_id=self._project.team_id,
                        project_id=self._project.id,
                        folder_id=self._folder.uuid,
                        priorities=priorities_to_upload,
                    )
                    self.reporter.update_progress(len(priorities_to_upload))
                    uploaded_score_names.extend(
                        list(map(lambda x: x["name"], res.get("data", [])))
                    )
                self.reporter.finish_progress()
                skipped_score_names = list(
                    set(initial_scores) - set(uploaded_score_names)
                )
                self._response.data = (uploaded_score_names, skipped_score_names)
            else:
                self.reporter.warning_messages("Empty scores.")
        return self._response


class DownloadAnnotations(BaseReportableUseCase):
    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        folder: FolderEntity,
        destination: str,
        recursive: bool,
        item_names: List[str],
        backend_service_provider: SuperannotateServiceProvider,
        items: BaseReadOnlyRepository,
        folders: BaseReadOnlyRepository,
        classes: BaseReadOnlyRepository,
        images: BaseManageableRepository,
        callback: Callable = None,
    ):
        super().__init__(reporter)
        self._project = project
        self._folder = folder
        self._destination = destination
        self._recursive = recursive
        self._item_names = item_names
        self._backend_client = backend_service_provider
        self._items = items
        self._folders = folders
        self._classes = classes
        self._callback = callback
        self._images = images

    def validate_item_names(self):
        if self._item_names:
            item_names = list(dict.fromkeys(self._item_names))
            len_unique_items, len_items = len(item_names), len(self._item_names)
            if len_unique_items < len_items:
                self.reporter.log_info(
                    f"Dropping duplicates. Found {len_unique_items}/{len_items} unique items."
                )
                self._item_names = item_names

    def validate_destination(self):
        if self._destination:
            destination = str(self._destination)
            if not os.path.exists(destination) or not os.access(
                destination, os.X_OK | os.W_OK
            ):
                raise AppException(
                    f"Local path {destination} is not an existing directory or access denied."
                )

    @property
    def destination(self) -> Path:
        return Path(self._destination if self._destination else "")

    def get_postfix(self):
        if self._project.type == constants.ProjectType.VECTOR:
            return "___objects.json"
        elif self._project.type == constants.ProjectType.PIXEL.value:
            return "___pixel.json"
        return ".json"

    def download_annotation_classes(self, path: str):
        response = self._backend_client.list_annotation_classes(
            team_id=self._project.team_id, project_id=self._project.id
        )
        if response.ok:
            classes_path = Path(path) / "classes"
            classes_path.mkdir(parents=True, exist_ok=True)
            with open(classes_path / "classes.json", "w+") as file:
                json.dump(
                    [i.dict(exclude_unset=True) for i in response.data], file, indent=4
                )
        else:
            self._response.errors = AppException("Cant download classes.")

    @staticmethod
    def get_items_count(path: str):
        return sum([len(files) for r, d, files in os.walk(path)])

    @staticmethod
    def coroutine_wrapper(coroutine):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        count = loop.run_until_complete(coroutine)
        loop.close()
        return count

    def execute(self):
        if self.is_valid():
            export_path = str(
                self.destination
                / Path(
                    f"{self._project.name} {datetime.now().strftime('%B %d %Y %H_%M')}"
                )
            )
            self.reporter.log_info(
                f"Downloading the annotations of the requested items to {export_path}\nThis might take a while…"
            )
            self.reporter.start_spinner()
            folders = []
            if self._folder.is_root and self._recursive:
                folders = self._folders.get_all(
                    Condition("team_id", self._project.team_id, EQ)
                    & Condition("project_id", self._project.id, EQ),
                )
                folders.append(self._folder)
            postfix = self.get_postfix()
            import nest_asyncio
            import platform

            if platform.system().lower() == "windows":
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

            nest_asyncio.apply()

            if not folders:
                loop = asyncio.new_event_loop()
                if not self._item_names:
                    condition = (
                            Condition("team_id", self._project.team_id, EQ)
                            & Condition("project_id", self._project.id, EQ)
                            & Condition("folder_id", self._folder.uuid, EQ)
                    )
                    item_names = [item.name for item in self._images.get_all(condition)]
                else:
                    item_names = self._item_names
                count = loop.run_until_complete(
                    self._backend_client.download_annotations(
                        team_id=self._project.team_id,
                        project_id=self._project.id,
                        folder_id=self._folder.uuid,
                        items=item_names,
                        reporter=self.reporter,
                        download_path=f"{export_path}{'/' + self._folder.name if not self._folder.is_root else ''}",
                        postfix=postfix,
                        callback=self._callback,
                    )
                )
            else:
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    coroutines = []
                    for folder in folders:
                        if not self._item_names:
                            condition = (
                                    Condition("team_id", self._project.team_id, EQ)
                                    & Condition("project_id", self._project.id, EQ)
                                    & Condition("folder_id", folder.uuid, EQ)
                            )
                            item_names = [item.name for item in self._images.get_all(condition)]
                        else:
                            item_names = self._item_names
                        coroutines.append(
                            self._backend_client.download_annotations(
                                team_id=self._project.team_id,
                                project_id=self._project.id,
                                folder_id=folder.uuid,
                                items=item_names,
                                reporter=self.reporter,
                                download_path=f"{export_path}{'/' + folder.name if not folder.is_root else ''}",  # noqa
                                postfix=postfix,
                                callback=self._callback,
                            )
                        )
                    count = sum(
                        [i for i in executor.map(self.coroutine_wrapper, coroutines)]
                    )

            self.reporter.stop_spinner()
            self.reporter.log_info(f"Downloaded annotations for {count} items.")
            self.download_annotation_classes(export_path)
            self._response.data = os.path.abspath(export_path)
        return self._response


class ValidateAnnotationUseCase(BaseReportableUseCase):
    DEFAULT_VERSION = "V1.00"
    SCHEMAS: Dict[str, Draft7Validator] = {}
    PATTERN_MAP = {
        "\\d{4}-[01]\\d-[0-3]\\dT[0-2]\\d:[0-5]\\d:[0-5]\\d(?:\\.\\d{3})Z": "YYYY-MM-DDTHH:MM:SS.fffZ"
    }

    def __init__(
        self,
        reporter: Reporter,
        team_id: int,
        project_type: int,
        annotation: dict,
        backend_service_provider: SuperannotateServiceProvider,
    ):
        super().__init__(reporter)
        self._team_id = team_id
        self._project_type = project_type
        self._annotation = annotation
        self._backend_client = backend_service_provider

    @staticmethod
    def _get_const(items, path=()):
        properties = items.get("properties", {})
        _type, _meta = properties.get("type"), properties.get("meta")
        if _meta and _meta.get("type"):
            path = path + ("meta",)
            path, _type = ValidateAnnotationUseCase._get_const(_meta, path)
        if _type and properties.get("type", {}).get("const"):
            path = path + ("type",)
            path, _type = path, properties["type"]["const"]
        return path, _type

    @staticmethod
    def _get_by_path(path: tuple, data: dict):
        tmp = data
        for i in path:
            tmp = tmp.get(i, {})
        return tmp

    @staticmethod
    def oneOf(validator, oneOf, instance, schema):  # noqa
        sub_schemas = enumerate(oneOf)
        const_key = None
        for index, sub_schema in sub_schemas:

            const_key, _type = ValidateAnnotationUseCase._get_const(sub_schema)
            if const_key:
                instance_type = ValidateAnnotationUseCase._get_by_path(
                    const_key, instance
                )
                if not instance_type:
                    yield ValidationError("type required")
                    return
                if const_key and instance_type == _type:
                    errs = list(
                        validator.descend(instance, sub_schema, schema_path=index)
                    )
                    if not errs:
                        return
                    yield ValidationError("invalid instance", context=errs)
                    return
            else:
                subschemas = enumerate(oneOf)
                all_errors = []
                for index, subschema in subschemas:
                    errs = list(
                        validator.descend(instance, subschema, schema_path=index)
                    )
                    if not errs:
                        break
                    all_errors.extend(errs)
                else:
                    yield ValidationError(
                        f"{instance!r} is not valid under any of the given schemas",
                        context=all_errors[:1],
                    )
                # yield from jsonschema._validators.oneOf(  # noqa
                #     validator, oneOf, instance, schema
                # )
        if const_key:
            yield ValidationError(f"invalid {'.'.join(const_key)}")

    @staticmethod
    def _pattern(validator, patrn, instance, schema):
        if validator.is_type(instance, "string") and not re.search(patrn, instance):
            yield ValidationError(
                f"{instance} does not match {ValidateAnnotationUseCase.PATTERN_MAP.get(patrn, patrn)}"
            )

    @staticmethod
    def iter_errors(self, instance, _schema=None):
        if _schema is None:
            _schema = self.schema
        if _schema is True:
            return
        elif _schema is False:
            yield jsonschema.exceptions.ValidationError(
                f"False schema does not allow {instance!r}",
                validator=None,
                validator_value=None,
                instance=instance,
                schema=_schema,
            )
            return

        scope = jsonschema.validators._id_of(_schema)  # noqa
        _schema = copy.copy(_schema)
        if scope:
            self.resolver.push_scope(scope)
        try:
            validators = []
            if "$ref" in _schema:
                ref = _schema.pop("$ref")
                validators.append(("$ref", ref))

            validators.extend(jsonschema.validators.iteritems(_schema))

            for k, v in validators:
                if k == "createdBy":
                    print()
                validator = self.VALIDATORS.get(k)
                if validator is None:
                    continue
                errors = validator(self, v, instance, _schema) or ()
                for error in errors:
                    # set details if not already set by the called fn
                    error._set(
                        validator=k,
                        validator_value=v,
                        instance=instance,
                        schema=_schema,
                    )
                    if k != "$ref":
                        error.schema_path.appendleft(k)
                    yield error
        finally:
            if scope:
                self.resolver.pop_scope()

    @staticmethod
    def extract_path(path):
        path = copy.copy(path)
        real_path = []
        for _ in range(len(path)):
            item = path.popleft()
            if isinstance(item, int):
                real_path.append(f"[{item}]")
            else:
                if real_path and not real_path[-1].endswith("]"):
                    real_path.extend([".", item])
                else:
                    real_path.append(item)
        return real_path

    def _get_validator(self, version: str) -> Draft7Validator:
        key = f"{self._project_type}__{version}"
        validator = ValidateAnnotationUseCase.SCHEMAS.get(key)
        if not validator:
            schema_response = self._backend_client.get_schema(
                self._team_id, self._project_type, version
            )
            if not schema_response.ok:
                raise AppException(f"Schema {version} does not exist.")
            validator = jsonschema.Draft7Validator(schema_response.data)
            from functools import partial

            iter_errors = partial(self.iter_errors, validator)
            validator.iter_errors = iter_errors
            validator.VALIDATORS["oneOf"] = self.oneOf
            validator.VALIDATORS["pattern"] = self._pattern
            ValidateAnnotationUseCase.SCHEMAS[key] = validator
        return validator

    def extract_messages(self, path, error, report):
        for sub_error in sorted(error.context, key=lambda e: e.schema_path):
            tmp_path = sub_error.path  # if sub_error.path else real_path
            _path = (
                f"{''.join(path)}"
                + ("." if tmp_path else "")
                + "".join(ValidateAnnotationUseCase.extract_path(tmp_path))
            )
            if sub_error.context:
                self.extract_messages(_path, sub_error, report)
            else:
                report.add(
                    (
                        _path,
                        sub_error.message,
                    )
                )

    def execute(self) -> Response:
        try:
            version = self._annotation["version"]
        except KeyError:
            version = self.DEFAULT_VERSION

        extract_path = ValidateAnnotationUseCase.extract_path
        validator = self._get_validator(version)
        errors = sorted(validator.iter_errors(self._annotation), key=lambda e: e.path)
        errors_report: Set[Tuple[str, str]] = set()
        if errors:
            for error in errors:
                if not error:
                    continue
                real_path = extract_path(error.path)
                if not error.context:
                    errors_report.add(("".join(real_path), error.message))
                self.extract_messages(real_path, error, errors_report)

        self._response.data = list(sorted(errors_report, key=lambda x: x[0]))
        return self._response
