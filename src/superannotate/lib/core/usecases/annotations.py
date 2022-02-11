import concurrent.futures
import io
import json
import os
from collections import namedtuple
from typing import List
from typing import Tuple

import boto3
import lib.core as constances
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
from lib.core.reporter import Reporter
from lib.core.repositories import BaseManageableRepository
from lib.core.service_types import UploadAnnotationAuthData
from lib.core.serviceproviders import SuerannotateServiceProvider
from lib.core.usecases.base import BaseReportableUseCae
from lib.core.usecases.images import GetBulkImages
from lib.core.usecases.images import ValidateAnnotationUseCase
from superannotate.logger import get_default_logger
from superannotate_schemas.validators import AnnotationValidators

logger = get_default_logger()


class UploadAnnotationsUseCase(BaseReportableUseCae):
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
        annotation_classes: List[AnnotationClassEntity],
        annotation_paths: List[str],
        backend_service_provider: SuerannotateServiceProvider,
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
        self._backend_service = backend_service_provider
        self._annotation_classes = annotation_classes
        self._annotation_paths = annotation_paths
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

    @property
    def annotation_postfix(self):
        if self._project.project_type in (
            constances.ProjectType.VIDEO.value,
            constances.ProjectType.DOCUMENT.value,
        ):
            return constances.ATTACHED_VIDEO_ANNOTATION_POSTFIX
        elif self._project.project_type == constances.ProjectType.VECTOR.value:
            return constances.VECTOR_ANNOTATION_POSTFIX
        elif self._project.project_type == constances.ProjectType.PIXEL.value:
            return constances.PIXEL_ANNOTATION_POSTFIX

    @staticmethod
    def extract_name(value: str):
        return os.path.basename(
            value.replace(constances.PIXEL_ANNOTATION_POSTFIX, "")
            .replace(constances.VECTOR_ANNOTATION_POSTFIX, "")
            .replace(constances.ATTACHED_VIDEO_ANNOTATION_POSTFIX, ""),
        )

    @property
    def annotations_to_upload(self):
        if not self._annotations_to_upload:
            annotation_paths = self._annotation_paths
            images_detail = []
            for annotation_path in annotation_paths:
                images_detail.append(
                    self.ImageInfo(
                        id=None,
                        path=annotation_path,
                        name=self.extract_name(annotation_path),
                    )
                )
            images_data = (
                GetBulkImages(
                    service=self._backend_service,
                    project_id=self._project.uuid,
                    team_id=self._project.team_id,
                    folder_id=self._folder.uuid,
                    images=[image.name for image in images_detail],
                )
                .execute()
                .data
            )
            for image_data in images_data:
                for idx, detail in enumerate(images_detail):
                    if detail.name == image_data.name:
                        images_detail[idx] = detail._replace(id=image_data.uuid)
                        break

            missing_annotations = list(
                filter(lambda image_detail: image_detail.id is None, images_detail)
            )
            annotations_to_upload = list(
                filter(lambda image_detail: image_detail.id is not None, images_detail)
            )
            if missing_annotations:
                logger.warning(
                    f"Couldn't find {len(missing_annotations)}/{len(annotations_to_upload + missing_annotations)} "
                    "items on the platform that match the annotations you want to upload."
                )
            self._missing_annotations = missing_annotations
            self._annotations_to_upload = annotations_to_upload
        return self._annotations_to_upload

    @property
    def missing_annotations(self):
        if not self._missing_annotations:
            self._missing_annotations = []
        return self._missing_annotations

    def get_annotation_upload_data(
        self, image_ids: List[int]
    ) -> UploadAnnotationAuthData:
        if self._pre_annotation:
            function = self._backend_service.get_pre_annotation_upload_data
        else:
            function = self._backend_service.get_annotation_upload_data
        response = function(
            project_id=self._project.uuid,
            team_id=self._project.team_id,
            folder_id=self._folder.uuid,
            image_ids=image_ids,
        )
        if response.ok:
            return response.data

    def _upload_annotation(
        self,
        image_id: int,
        image_name: str,
        upload_data: UploadAnnotationAuthData,
        path: str,
        bucket,
    ):
        try:
            self.reporter.disable_warnings()
            response = UploadAnnotationUseCase(
                project=self._project,
                folder=self._folder,
                team=self._team,
                image=ImageEntity(
                    uuid=image_id,
                    name=image_name,
                    team_id=self._project.team_id,
                    project_id=self._project.uuid,
                ),
                images=self._images,
                annotation_classes=self._annotation_classes,
                backend_service_provider=self._backend_service,
                reporter=self.reporter,
                templates=self._templates,
                annotation_upload_data=upload_data,
                client_s3_bucket=self._client_s3_bucket,
                annotation_path=path,
                verbose=False,
                s3_bucket=bucket,
                validators=self._validators,
            ).execute()
            if response.errors:
                return path, False
            return path, True
        except Exception as e:
            logger.debug(str(e), exc_info=True)
            return path, False
        finally:
            self.reporter.enable_warnings()

    def get_bucket_to_upload(self, ids: List[int]):
        upload_data = self.get_annotation_upload_data(ids)
        if upload_data:
            session = boto3.Session(
                aws_access_key_id=upload_data.access_key,
                aws_secret_access_key=upload_data.secret_key,
                aws_session_token=upload_data.session_token,
                region_name=upload_data.region,
            )
            resource = session.resource("s3")
            return resource.Bucket(upload_data.bucket)

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
                f"{len(self.annotations_to_upload + self.missing_annotations)} annotations from {self._folder_path}. "
                f"{constances.USE_VALIDATE_MESSAGE}"
            )

    def execute(self):
        uploaded_annotations = []
        failed_annotations = []
        if self.annotations_to_upload:
            iterations_range = range(
                0, len(self.annotations_to_upload), self.AUTH_DATA_CHUNK_SIZE
            )
            self.reporter.start_progress(
                len(self.annotations_to_upload), description="Uploading Annotations"
            )
            for step in iterations_range:
                annotations_to_upload = self.annotations_to_upload[
                    step : step + self.AUTH_DATA_CHUNK_SIZE  # noqa: E203
                ]
                upload_data = self.get_annotation_upload_data(
                    [int(image.id) for image in annotations_to_upload]
                )
                bucket = self.get_bucket_to_upload(
                    [int(image.id) for image in annotations_to_upload]
                )
                if bucket:
                    image_id_name_map = {
                        image.id: image for image in self.annotations_to_upload
                    }
                    # dummy progress
                    for _ in range(
                        len(annotations_to_upload) - len(upload_data.images)
                    ):
                        self.reporter.update_progress()
                    with concurrent.futures.ThreadPoolExecutor(
                        max_workers=self.MAX_WORKERS
                    ) as executor:
                        results = [
                            executor.submit(
                                self._upload_annotation,
                                image_id,
                                image_id_name_map[image_id].name,
                                upload_data,
                                image_id_name_map[image_id].path,
                                bucket,
                            )
                            for image_id, image_data in upload_data.images.items()
                        ]
                        for future in concurrent.futures.as_completed(results):
                            annotation, uploaded = future.result()
                            if uploaded:
                                uploaded_annotations.append(annotation)
                            else:
                                failed_annotations.append(annotation)
                            self.reporter.update_progress()
            self.reporter.finish_progress()
            self._log_report()
        self._response.data = (
            uploaded_annotations,
            failed_annotations,
            [annotation.path for annotation in self.missing_annotations],
        )
        return self._response


class UploadAnnotationUseCase(BaseReportableUseCae):
    def __init__(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        image: ImageEntity,
        images: BaseManageableRepository,
        team: TeamEntity,
        annotation_classes: List[AnnotationClassEntity],
        backend_service_provider: SuerannotateServiceProvider,
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
                project_id=self._project.uuid,
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
                if self._project.project_type == constances.ProjectType.PIXEL.value:
                    self._mask = self.get_s3_file(
                        self.from_s3,
                        self._annotation_path.replace(
                            constances.PIXEL_ANNOTATION_POSTFIX,
                            constances.ANNOTATION_MASK_POSTFIX,
                        ),
                    )
            else:
                self._annotation_json = json.load(open(self._annotation_path))
                if self._project.project_type == constances.ProjectType.PIXEL.value:
                    self._mask = open(
                        self._annotation_path.replace(
                            constances.PIXEL_ANNOTATION_POSTFIX,
                            constances.ANNOTATION_MASK_POSTFIX,
                        ),
                        "rb",
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

    def clean_json(self, json_data: dict,) -> Tuple[bool, dict]:
        use_case = ValidateAnnotationUseCase(
            constances.ProjectType.get_name(self._project.project_type),
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
                bucket = self.s3_bucket
                annotation_json = self.prepare_annotations(
                    project_type=self._project.project_type,
                    annotations=self._annotation_json,
                    annotation_classes=self._annotation_classes,
                    templates=self._templates,
                    reporter=self.reporter,
                    team=self._team,
                )
                bucket.put_object(
                    Key=self.annotation_upload_data.images[self._image.uuid][
                        "annotation_json_path"
                    ],
                    Body=json.dumps(annotation_json),
                )
                if (
                    self._project.project_type == constances.ProjectType.PIXEL.value
                    and self._mask
                ):
                    bucket.put_object(
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
