import asyncio
import concurrent.futures
import io
import json
import os
import platform
from collections import defaultdict
from collections import namedtuple
from datetime import datetime
from pathlib import Path
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

import boto3
from jsonschema import Draft7Validator
from jsonschema import ValidationError
from superannotate_schemas.validators import AnnotationValidators

import lib.core as constances
from lib.core.conditions import CONDITION_EQ as EQ
from lib.core.conditions import Condition
from lib.core.data_handlers import ChainedAnnotationHandlers
from lib.core.data_handlers import DocumentTagHandler
from lib.core.data_handlers import LastActionHandler
from lib.core.data_handlers import MissingIDsHandler
from lib.core.data_handlers import VideoFormatHandler
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
from lib.core.service_types import ServiceResponse
from lib.core.service_types import UploadAnnotationAuthData
from lib.core.serviceproviders import SuperannotateServiceProvider
from lib.core.types import PriorityScore
from lib.core.usecases.base import BaseReportableUseCase
from lib.core.usecases.images import ValidateAnnotationUseCase
from lib.core.video_convertor import VideoFrameGenerator
from superannotate.logger import get_default_logger

logger = get_default_logger()

if platform.system().lower() == "windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class UploadAnnotationsUseCase(BaseReportableUseCase):
    MAX_WORKERS = 10
    CHUNK_SIZE = 100
    AUTH_DATA_CHUNK_SIZE = 500
    ImageInfo = namedtuple("ImageInfo", ["path", "name", "id"])

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
            root_annotation_paths: str,
            backend_service_provider: SuperannotateServiceProvider,
            templates: List[dict],
            validators: AnnotationValidators,
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
        self._root_annotation_paths = root_annotation_paths
        self._client_s3_bucket = client_s3_bucket
        self._pre_annotation = pre_annotation
        self._templates = templates
        self._annotations_to_upload = []
        self._missing_annotations = []
        self._validators = validators
        self.missing_attribute_groups = set()
        self.missing_classes = set()
        self.missing_attributes = set()
        self._folder_path = folder_path
        self._folder_annotations_map: Dict[int, List[str]] = self.map_folder_to_annotation(annotation_paths)

    def map_folder_to_annotation(self, annotation_paths):
        folder_annotations_map: Dict[int, List[str]] = defaultdict(list)

        def get_folder_name(file_path: str):
            tmp = file_path[len(self._root_annotation_paths):]
            if not tmp:
                tmp = "root"
            return tmp

        for item_path in annotation_paths:
            path, _ = os.path.split(item_path)
            folder_annotations_map[self._get_folder_id(get_folder_name(path))].append(item_path)
        return folder_annotations_map

    def _get_folder_id(self, name):
        try:
            condition = (
                    Condition("name", name, EQ)
                    & Condition("team_id", self._project.team_id, EQ)
                    & Condition("project_id", self._project.id, EQ)
            )
            folder = self._folders.get_one(condition)
            if folder:
                return folder.id
        except AppException:
            # TODO add error msg
            pass

    @property
    def annotation_postfix(self):
        if self._project.type in (
                constances.ProjectType.VIDEO.value,
                constances.ProjectType.DOCUMENT.value,
        ):
            return constances.ATTACHED_VIDEO_ANNOTATION_POSTFIX
        elif self._project.type == constances.ProjectType.VECTOR.value:
            return constances.VECTOR_ANNOTATION_POSTFIX
        elif self._project.type == constances.ProjectType.PIXEL.value:
            return constances.PIXEL_ANNOTATION_POSTFIX

    @staticmethod
    def extract_name(value: str):
        return os.path.basename(
            value.replace(constances.PIXEL_ANNOTATION_POSTFIX, "")
                .replace(constances.VECTOR_ANNOTATION_POSTFIX, "")
                .replace(constances.ATTACHED_VIDEO_ANNOTATION_POSTFIX, ""),
        )

    @property
    def missing_annotations(self):
        if not self._missing_annotations:
            self._missing_annotations = []
        return self._missing_annotations

    def _log_report(self):
        for key, values in self.reporter.custom_messages.items():
            if key in [
                "missing_classes",
                "missing_attribute_groups",
                "missing_attributes",
            ]:
                template = key + ": {}"
                if key == "missing_classes":
                    template = "Could not find annotation classes matching existing classes on the platform: [{}]"
                elif key == "missing_attribute_groups":
                    template = (
                        "Could not find attribute groups matching existing attribute groups"
                        " on the platform: [{}]"
                    )
                elif key == "missing_attributes":
                    template = "Could not find attributes matching existing attributes on the platform: [{}]"
                logger.warning(template.format("', '".join(values)))
        if self.reporter.custom_messages.get("invalid_jsons"):
            logger.warning(
                f"Couldn't validate {len(self.reporter.custom_messages['invalid_jsons'])}/"
                f"{len(self._annotation_paths)} annotations from {self._folder_path}. "
                f"{constances.USE_VALIDATE_MESSAGE}"
            )

    @staticmethod
    def prepare_annotations(
            project_type: int,
            annotations: dict,
            annotation_classes: List[AnnotationClassEntity],
            templates: List[dict],
            reporter: Reporter,
            team: TeamEntity,
    ) -> dict:
        handlers_chain = ChainedAnnotationHandlers()
        if project_type in (
                constances.ProjectType.VECTOR.value,
                constances.ProjectType.PIXEL.value,
                constances.ProjectType.DOCUMENT.value,
        ):
            handlers_chain.attach(
                MissingIDsHandler(annotation_classes, templates, reporter)
            )
        elif project_type == constances.ProjectType.VIDEO.value:
            handlers_chain.attach(VideoFormatHandler(annotation_classes, reporter))
        if project_type == constances.ProjectType.DOCUMENT.value:
            handlers_chain.attach(DocumentTagHandler(annotation_classes))
        handlers_chain.attach(LastActionHandler(team.creator_id))
        return handlers_chain.handle(annotations)

    @staticmethod
    def get_annotation_from_s3(bucket, path: str):
        session = boto3.Session().resource("s3")
        file = io.BytesIO()
        s3_object = session.Object(bucket, path)
        s3_object.download_fileobj(file)
        file.seek(0)
        return file

    def prepare_annotation(self, annotation: dict):
        use_case = ValidateAnnotationUseCase(
            constances.ProjectType.get_name(self._project.type),
            annotation=annotation,
            validators=self._validators,
        )
        is_valid, clean_json = use_case.execute().data
        if is_valid:
            annotation_json = self.prepare_annotations(
                project_type=self._project.type,
                annotations=clean_json,
                annotation_classes=self._annotation_classes,
                templates=self._templates,
                reporter=self.reporter,
                team=self._team,
            )
            annotation_file = io.StringIO()
            json.dump(annotation_json, annotation_file)
            annotation_file.seek(0)
            return annotation_file

    def get_annotation(self, path: str) -> Tuple[io.StringIO, Optional[io.BytesIO]]:
        mask = None
        if self._client_s3_bucket:
            annotation = json.load(self.get_annotation_from_s3(self._client_s3_bucket, path))
        else:
            annotation = json.load(open(path))
            if self._project.type == constances.ProjectType.PIXEL.value:
                mask = open(path.replace(constances.PIXEL_ANNOTATION_POSTFIX, constances.ANNOTATION_MASK_POSTFIX), "rb")
        annotation = self.prepare_annotation(annotation)
        if not annotation:
            self.reporter.store_message("invalid_jsons", path)
        return annotation, mask

    def execute(self):
        uploaded_annotations = []
        failed_annotations = []
        self.reporter.start_progress(len(self._annotation_paths), description="Uploading Annotations")
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as executor:
            results = {}
            for folder_id, annotation_paths in self._folder_annotations_map.items():
                name_path_map = {}
                for step in range(0, len(annotation_paths), self.CHUNK_SIZE):
                    items_name_file_map = {}
                    for annotation_path in annotation_paths[step: step + self.CHUNK_SIZE]:  # noqa: E203
                        annotation, mask = self.get_annotation(annotation_path)
                        annotation_name = self.extract_name(annotation_path)
                        items_name_file_map[annotation_name] = annotation
                        name_path_map[annotation_name] = annotation_path
                    results[
                        executor.submit(
                            self._backend_service.upload_annotations,
                            team_id=self._project.team_id,
                            project_id=self._project.id,
                            folder_id=folder_id,
                            items_name_file_map=items_name_file_map
                        )] = len(items_name_file_map), name_path_map

            for future in concurrent.futures.as_completed(results.keys()):
                response: ServiceResponse = future.result()
                items_count, name_path_map = results[future]
                if response.ok:
                    if response.data.failedItems:  # noqa
                        failed_annotations.extend(
                            [name_path_map.pop(failed_item) for failed_item in response.data.failedItems]
                        )
                    uploaded_annotations.extend(name_path_map.values())
                self.reporter.update_progress(results[future][0])

            self.reporter.finish_progress()
            self._log_report()
        self._response.data = (
            uploaded_annotations,
            failed_annotations,
            [annotation.path for annotation in self.missing_annotations],
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
            validators: AnnotationValidators,
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
        self._validators = validators

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

    def set_annotation_json(self):
        if not self._annotation_json:
            if self._client_s3_bucket:
                self._annotation_json = json.load(
                    self.get_s3_file(self.from_s3, self._annotation_path)
                )
                if self._project.type == constances.ProjectType.PIXEL.value:
                    self._mask = self.get_s3_file(
                        self.from_s3,
                        self._annotation_path.replace(
                            constances.PIXEL_ANNOTATION_POSTFIX,
                            constances.ANNOTATION_MASK_POSTFIX,
                        ),
                    )
            else:
                self._annotation_json = json.load(open(self._annotation_path))
                if self._project.type == constances.ProjectType.PIXEL.value:
                    self._mask = open(
                        self._annotation_path.replace(
                            constances.PIXEL_ANNOTATION_POSTFIX,
                            constances.ANNOTATION_MASK_POSTFIX,
                        ),
                        "rb",
                    )

    def clean_json(
            self,
            json_data: dict,
    ) -> Tuple[bool, dict]:
        use_case = ValidateAnnotationUseCase(
            constances.ProjectType.get_name(self._project.type),
            annotation=json_data,
            validators=self._validators,
        )
        return use_case.execute().data

    def execute(self):
        if self.is_valid():
            self.set_annotation_json()
            is_valid, clean_json = self.clean_json(self._annotation_json)
            if is_valid:
                self._annotation_json = clean_json

                annotation_json = UploadAnnotationsUseCase.prepare_annotations(
                    project_type=self._project.type,
                    annotations=self._annotation_json,
                    annotation_classes=self._annotation_classes,
                    templates=self._templates,
                    reporter=self.reporter,
                    team=self._team,
                )
                annotation_file = io.StringIO()
                json.dump(annotation_json, annotation_file)
                annotation_file.seek(0)
                self._backend_service.upload_annotations(
                    team_id=self._project.team_id, project_id=self._project.id, folder_id=self._folder.uuid,
                    items_name_file_map={self._image.name: annotation_file}
                )
                if (
                        self._project.type == constances.ProjectType.PIXEL.value
                        and self._mask
                ):
                    self.s3_bucket.put_object(
                        Key=self.annotation_upload_data.images[self._image.uuid][
                            "annotation_bluemap_path"
                        ],
                        Body=self._mask,
                    )
                self._image.annotation_status_code = (
                    constances.AnnotationStatus.IN_PROGRESS.value
                )
                self._images.update(self._image)
                if self._verbose:
                    self.reporter.log_info(
                        f"Uploading annotations for image {str(self._image.name)} in project {self._project.name}."
                    )
            else:
                self._response.errors = constances.INVALID_JSON_MESSAGE
                self.reporter.store_message("invalid_jsons", self._annotation_path)
                self.reporter.log_warning(
                    f"Couldn't validate annotations. {constances.USE_VALIDATE_MESSAGE}"
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
        if self._project.type == constances.ProjectType.PIXEL.value:
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
        if self._project.type != constances.ProjectType.VIDEO.value:
            raise AppException(
                "The function is not supported for"
                f" {constances.ProjectType.get_name(self._project.type)} projects."
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
                                           i: i + self.CHUNK_SIZE
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
        if self._project.type == constances.ProjectType.VECTOR:
            return "___objects.json"
        elif self._project.type == constances.ProjectType.PIXEL.value:
            return "___pixel.json"
        return ".json"

    def download_annotation_classes(self, path: str):
        classes = self._classes.get_all()
        classes_path = Path(path) / "classes"
        classes_path.mkdir(parents=True, exist_ok=True)
        with open(classes_path / "classes.json", "w+") as file:
            json.dump([i.dict() for i in classes], file, indent=4)

    @staticmethod
    def get_items_count(path: str):
        return sum([len(files) for r, d, files in os.walk(path)])

    @staticmethod
    def coroutine_wrapper(coroutine):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(coroutine)
        loop.close()

    def execute(self):
        if self.is_valid():
            export_path = str(
                self.destination
                / Path(f"{self._project.name} {datetime.now().strftime('%B %d %Y %H_%M')}")
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
                loop.run_until_complete(
                    self._backend_client.download_annotations(
                        team_id=self._project.team_id,
                        project_id=self._project.id,
                        folder_id=self._folder.uuid,
                        items=self._item_names,
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
                        coroutines.append(
                            self._backend_client.download_annotations(
                                team_id=self._project.team_id,
                                project_id=self._project.id,
                                folder_id=folder.uuid,
                                items=self._item_names,
                                reporter=self.reporter,
                                download_path=f"{export_path}{'/' + folder.name if not folder.is_root else ''}",  # noqa
                                postfix=postfix,
                                callback=self._callback,
                            )
                        )
                    _ = [_ for _ in executor.map(self.coroutine_wrapper, coroutines)]

            self.reporter.stop_spinner()
            self.reporter.log_info(
                f"Downloaded annotations for {self.get_items_count(export_path)} items."
            )
            self.download_annotation_classes(export_path)
            self._response.data = os.path.abspath(export_path)
        return self._response


class ValidateAnnotations(BaseReportableUseCase):
    SCHEMAS: Dict[str: str]

    def __init__(
            self,
            reporter: Reporter,
            project: ProjectEntity,
            annotations: List[dict],
            default_version: str,
            backend_service_provider: SuperannotateServiceProvider
    ):
        super().__init__(reporter)
        self._project = project
        self._annotation = annotations
        self._default_version = default_version
        self._backend_client = backend_service_provider

    @staticmethod
    def _get_const(items):
        return next(((key, value) for key, value in items if isinstance(value, dict) and value.get("const")),
                    (None, None))

    @staticmethod
    def oneOf(validator, oneOf, instance, schema):
        subschemas = enumerate(oneOf)
        all_errors = []
        const_match = False
        first_valid = None
        for index, subschema in subschemas:
            key, _type = ValidateAnnotations._get_const(subschema["properties"].items())
            if key:
                if instance[key] != _type["const"]:
                    continue
            errs = list(validator.descend(instance, subschema, schema_path=index))
            if not errs:
                first_valid = subschema
                break
            const_match = True
            all_errors.extend(errs)
        else:
            if const_match:
                yield ValidationError("invalid instance", context=all_errors)
            else:
                yield ValidationError("instance is not valid under any schemas")

        more_valid = [s for i, s in subschemas if validator.is_valid(instance, s)]
        if more_valid:
            if first_valid:
                more_valid.append(first_valid)
            reprs = ", ".join(repr(schema) for schema in more_valid)
            yield ValidationError(
                "%r is valid under each of %s" % (instance, reprs)
            )

    @staticmethod
    def extract_path(path):
        real_path = []
        for item in path:
            if isinstance(item, str):
                if real_path:
                    real_path.append(".")
                real_path.append(item)
            elif isinstance(item, int):
                real_path.append(f"[{item}]")
        return real_path

    def _get_schema(self, project_type: int, version: str):
        key = f"{project_type}__{version}"
        schema = ValidateAnnotations.SCHEMAS.get(key, self._backend_client.get_schema(project_type, version))
        if not schema:
            raise AppException(f"Schema {version} does not exist.")
        ValidateAnnotations.SCHEMAS[key] = schema
        return schema

    def _validate_annotation(self, annotation: dict, version: str) -> Tuple[dict, List[Tuple[str, str]]]:
        extract_path = ValidateAnnotations.extract_path
        validator = Draft7Validator(self._get_schema(self._project.type, version))
        validator.VALIDATORS["oneOf"] = self.oneOf
        errors = sorted(validator.iter_errors(annotation), key=lambda e: e.path)
        errors_report: List[Tuple[str, str]] = []
        if errors:
            for error in errors:
                real_path = extract_path(error.path)
                if not error.context:
                    errors_report.append(("".join(real_path), error.message))
                for sub_error in sorted(error.context, key=lambda e: e.schema_path):
                    tmp_path = sub_error.path if sub_error.path else real_path
                    errors_report.append(
                        (f"{''.join(real_path)}." + "".join(extract_path(tmp_path)),
                         sub_error.message)
                    )
        return annotation, errors_report

    def execute(self) -> Response:
        valid_annotations = []
        errors_report = []
        for annotation in self._annotation:
            version = annotation.get("version", self._default_version)
            annotation, error = self._validate_annotation(annotation, version)
            if annotation:
                valid_annotations.append(annotation)
            else:
                errors_report.append(error)
        return self._response
