import concurrent.futures
import copy
import io
import json
import logging
import os.path
import random
import tempfile
import time
import uuid
from collections import defaultdict
from collections import namedtuple
from pathlib import Path
from typing import List
from typing import Optional

import boto3
import cv2
import lib.core as constances
import numpy as np
import requests
from botocore.exceptions import ClientError
from lib.core.conditions import Condition
from lib.core.conditions import CONDITION_EQ as EQ
from lib.core.entities import AnnotationClassEntity
from lib.core.entities import BaseItemEntity
from lib.core.entities import FolderEntity
from lib.core.entities import ImageEntity
from lib.core.entities import ProjectEntity
from lib.core.entities import S3FileEntity
from lib.core.enums import ImageQuality
from lib.core.enums import ProjectType
from lib.core.exceptions import AppException
from lib.core.exceptions import AppValidationException
from lib.core.exceptions import ImageProcessingException
from lib.core.plugin import ImagePlugin
from lib.core.plugin import VideoPlugin
from lib.core.reporter import Progress
from lib.core.reporter import Reporter
from lib.core.repositories import BaseManageableRepository
from lib.core.response import Response
from lib.core.serviceproviders import BaseServiceProvider
from lib.core.types import Attachment
from lib.core.types import AttachmentMeta
from lib.core.usecases.base import BaseInteractiveUseCase
from lib.core.usecases.base import BaseReportableUseCase
from lib.core.usecases.base import BaseUseCase
from PIL import UnidentifiedImageError

logger = logging.getLogger("sa")


class GetImageUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        image_name: str,
        service_provider: BaseServiceProvider,
    ):
        super().__init__()
        self._project = project
        self._folder = folder
        self._image_name = image_name
        self._service_provider = service_provider

    def execute(self):
        images = self._service_provider.items.list_by_names(
            project=self._project, folder=self._folder, names=[self._image_name]
        ).data
        if images:
            self._response.data = images[0]
        else:
            raise AppException("Image not found.")
        return self._response


class AttachFileUrlsUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        attachments: List[ImageEntity],
        service_provider: BaseServiceProvider,
        annotation_status: str = None,
        upload_state_code: int = constances.UploadState.EXTERNAL.value,
    ):
        super().__init__()
        self._attachments = attachments
        self._project = project
        self._folder = folder
        self._service_provider = service_provider
        self._annotation_status = annotation_status
        self._upload_state_code = upload_state_code

    def _validate_limitations(self, to_upload_count):
        response = self._service_provider.get_limitations(self._project, self._folder)
        if not response.ok:
            raise AppValidationException(response.error)
        if to_upload_count > response.data.folder_limit.remaining_image_count:
            raise AppValidationException(constances.ATTACH_FOLDER_LIMIT_ERROR_MESSAGE)
        elif to_upload_count > response.data.project_limit.remaining_image_count:
            raise AppValidationException(constances.ATTACH_PROJECT_LIMIT_ERROR_MESSAGE)
        elif (
            response.data.user_limit
            and to_upload_count > response.data.user_limit.remaining_image_count
        ):
            raise AppValidationException(constances.ATTACH_USER_LIMIT_ERROR_MESSAGE)

    @property
    def annotation_status_code(self):
        if self._annotation_status:
            if isinstance(self._annotation_status, int):
                return self._annotation_status
            return constances.AnnotationStatus.get_value(self._annotation_status)
        return constances.AnnotationStatus.NOT_STARTED.value

    @property
    def upload_state_code(self) -> int:
        if not self._upload_state_code:
            return constances.UploadState.EXTERNAL.value
        return self._upload_state_code

    def execute(self):
        response = self._service_provider.items.list_by_names(
            project=self._project,
            folder=self._folder,
            names=[image.name for image in self._attachments],
        )
        if not response.ok:
            raise AppException(response.error)
        duplications = [image.name for image in response.data]
        meta = {}
        to_upload = []
        for image in self._attachments:
            if not image.name:
                image.name = str(uuid.uuid4())
            if image.name not in duplications:
                to_upload.append(Attachment(**{"name": image.name, "path": image.path}))
                meta[image.name] = AttachmentMeta(
                    **{
                        "width": image.meta["width"],
                        "height": image.meta["height"],
                    }
                )
        try:
            self._validate_limitations(len(to_upload))
        except AppValidationException as e:
            self._response.errors = e
            return self._response
        if to_upload:
            backend_response = self._service_provider.items.attach(
                project=self._project,
                folder=self._folder,
                attachments=to_upload,
                annotation_status_code=self.annotation_status_code,
                upload_state_code=self.upload_state_code,
                meta=meta,
            )
            if isinstance(backend_response, dict) and "error" in backend_response:
                self._response.errors = AppException(backend_response["error"])
            else:
                self._response.data = backend_response.data, duplications
        else:
            self._response.data = [], duplications
        return self._response


class GetImageBytesUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        image: ImageEntity,
        service_provider: BaseServiceProvider,
        image_variant: str = "original",
    ):
        super().__init__()
        self._project = project
        self._folder = folder
        self._image = image
        self._service_provider = service_provider
        self._image_variant = image_variant

    def execute(self):
        auth_data = self._service_provider.get_download_token(
            project=self._project,
            folder=self._folder,
            image_id=self._image.id,
            include_original=1,
        ).data
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
        from_image: BaseItemEntity,
        to_image: BaseItemEntity,
        from_folder: FolderEntity,
        to_folder: FolderEntity,
        service_provider: BaseServiceProvider,
        from_project_s3_repo: BaseManageableRepository,
        to_project_s3_repo: BaseManageableRepository,
        annotation_type: str = "MAIN",
    ):
        super().__init__()
        self._from_project = from_project
        self._to_project = to_project
        self._from_folder = from_folder
        self._to_folder = to_folder
        self._from_image = from_image
        self._to_image = to_image
        self._service_provider = service_provider
        self._from_project_s3_repo = from_project_s3_repo
        self.to_project_s3_repo = to_project_s3_repo
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
    def download_auth_data(self):
        return self._service_provider.get_download_token(
            project=self._from_project,
            folder=self._from_folder,
            image_id=self._from_image.id,
            include_original=1,
        ).data

    @property
    def upload_auth_data(self):
        return self._service_provider.get_upload_token(
            project=self._to_project,
            folder=self._to_folder,
            image_id=self._to_image.id,
        ).data

    def validate_project_type(self):
        if self._from_project.type != self._to_project.type:
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
            self._service_provider.annotation_classes.list(
                Condition("project_id", self._from_project.id, EQ)
            ).data
        )
        to_project_annotation_classes = self._service_provider.annotation_classes.list(
            Condition("project_id", self._to_project.id, EQ)
        ).data
        annotations_classes_from_copy = {
            from_annotation.id: from_annotation
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
                            if group.id == attribute["groupId"]:
                                attribute["groupName"] = group.name
                                attribute_group = group
                        if attribute.get("id") and attribute_group:
                            for attr in attribute_group.attributes:
                                if attr.id == attribute["id"]:
                                    attribute["name"] = attr.name

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
                group.name: group for group in annotation_class.attribute_groups
            }
            instance["classId"] = annotation_class.id
            for attribute in instance["attributes"]:
                if attribute_groups_map.get(attribute["groupName"]):
                    attribute["groupId"] = attribute_groups_map[
                        attribute["groupName"]
                    ].id
                    attr_map = {
                        attr.name: attr
                        for attr in attribute_groups_map[
                            attribute["groupName"]
                        ].attributes
                    }
                    if attribute["name"] not in attr_map:
                        del attribute["groupId"]
                        continue
                    attribute["id"] = attr_map[attribute["name"]].id

        auth_data = self.upload_auth_data
        file = S3FileEntity(
            uuid=auth_data["annotation_json_path"]["filePath"],
            data=json.dumps(image_annotations),
        )
        self.to_project_s3_repo.insert(file)

        if (
            self._to_project.type == constances.ProjectType.PIXEL.value
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


class UpdateItemUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        item: BaseItemEntity,
        service_provider: BaseServiceProvider,
    ):
        super().__init__()
        self._project = project
        self._service_provider = service_provider
        self._item = item

    def execute(self):
        self._service_provider.items.update(project=self._project, item=self._item)
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
            self._annotations = json.load(open(f"{image_path}.json"))
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
                    Image(
                        "fuse",
                        f"{self._image_path}___fuse.png",
                        image.get_empty(),
                    )
                ]
                if self._generate_overlay:
                    images.append(
                        Image("overlay", f"{self._image_path}___overlay.png", image)
                    )

                outline_color = 4 * (255,)
                for instance in self.annotations["instances"]:
                    if (not instance.get("className")) or (
                        not class_color_map.get(instance["className"])
                    ):
                        continue
                    color = class_color_map.get(instance["className"])
                    if not color:
                        class_color_map[instance["className"]] = self.generate_color()
                    for image in images:
                        fill_color = (
                            *class_color_map[instance["className"]],
                            255 if image.type == "fuse" else self.TRANSPARENCY,
                        )
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
                                    *points, fill_color, fill_color, fixed=True
                                )
                            for connection in instance["connections"]:
                                image.content.draw_line(
                                    points_id_map[connection["from"]],
                                    points_id_map[connection["to"]],
                                    fill_color=fill_color,
                                )
            else:
                if not os.path.exists(self.blue_mask_path):
                    logger.warning(
                        "There is no blue map to generate fuse or overlay images."
                    )
                    return self._response
                image = ImagePlugin(io.BytesIO(file.read()))
                annotation_mask = np.array(
                    ImagePlugin(
                        io.BytesIO(open(self.blue_mask_path, "rb").read())
                    ).content
                )
                weight, height = image.get_size()
                empty_image_arr = np.full((height, weight, 4), [0, 0, 0, 255], np.uint8)
                for annotation in self.annotations["instances"]:
                    if (not annotation.get("className")) or (
                        not class_color_map.get(annotation["className"])
                    ):
                        continue
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

                if self._generate_overlay:
                    alpha = 0.5  # transparency measure
                    overlay = copy.copy(empty_image_arr)
                    overlay[:, :, :3] = np.array(image.content)[:, :, :3]
                    overlay = ImagePlugin.from_array(
                        cv2.addWeighted(empty_image_arr, alpha, overlay, 1 - alpha, 0)
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


class GetS3ImageUseCase(BaseUseCase):
    def __init__(
        self,
        s3_bucket,
        image_path: str,
    ):
        super().__init__()
        self._s3_bucket = s3_bucket
        self._image_path = image_path

    def execute(self):
        try:
            image = io.BytesIO()
            session = boto3.Session()
            resource = session.resource("s3")
            image_object = resource.Object(self._s3_bucket, self._image_path)
            if image_object.content_length > constances.MAX_IMAGE_SIZE:
                raise AppValidationException(
                    f"File size is {image_object.content_length}"
                )
            image_object.download_fileobj(image)
            self._response.data = image
        except ClientError as e:
            self._response.errors = str(e)
        return self._response


class DownloadImageUseCase(BaseReportableUseCase):
    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        folder: FolderEntity,
        image: ImageEntity,
        service_provider: BaseServiceProvider,
        download_path: str,
        image_variant: str = "original",
        include_annotations: bool = False,
        include_fuse: bool = False,
        include_overlay: bool = False,
    ):
        super().__init__(reporter)
        self._project = project
        self._image = image
        self._download_path = download_path
        self._image_variant = image_variant
        self._include_fuse = include_fuse
        self._include_overlay = include_overlay
        self._include_annotations = include_annotations
        self._service_provider = service_provider
        self.get_image_use_case = GetImageBytesUseCase(
            project=self._project,
            folder=folder,
            image=image,
            service_provider=service_provider,
            image_variant=image_variant,
        )
        self.download_annotation_use_case = DownloadImageAnnotationsUseCase(
            service_provider=service_provider,
            project=project,
            folder=folder,
            image_name=self._image.name,
            destination=download_path,
        )

    def validate_project_type(self):
        if (
            self._project.type in constances.LIMITED_FUNCTIONS
            or self._project.upload_state == constances.UploadState.EXTERNAL.value
        ):
            raise AppValidationException(
                "The feature does not support projects containing attached URLs."
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
            fuse_image = None
            annotations = None

            image_bytes = self.get_image_use_case.execute().data
            download_path = f"{self._download_path}/{self._image.name}"
            if self._image_variant == "lores":
                download_path = download_path + "___lores.jpg"
            with open(download_path, "wb") as image_file:
                image_file.write(image_bytes.getbuffer())

            if self._include_annotations:
                annotations = self.download_annotation_use_case.execute().data

            if self._include_annotations and (
                self._include_fuse or self._include_overlay
            ):
                classes = self._service_provider.annotation_classes.list(
                    Condition("project_id", self._project.id, EQ)
                ).data
                fuse_image = (
                    CreateFuseImageUseCase(
                        project_type=constances.ProjectType.get_name(
                            self._project.type
                        ),
                        image_path=download_path,
                        classes=[
                            annotation_class.dict(exclude_unset=True)
                            for annotation_class in classes
                        ],
                        generate_overlay=self._include_overlay,
                    )
                    .execute()
                    .data
                )

            self._response.data = (
                download_path,
                annotations,
                fuse_image,
            )

        return self._response


class UploadImageToProject(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        s3_repo,
        service_provider: BaseServiceProvider,
        annotation_status: str,
        image_bytes: io.BytesIO = None,
        image_path: str = None,
        image_name: str = None,
        from_s3_bucket: str = None,
        image_quality_in_editor: str = None,
    ):
        super().__init__()
        self._project = project
        self._folder = folder
        self._image_bytes = image_bytes
        self._image_path = image_path
        self._image_name = image_name
        self._from_s3_bucket = from_s3_bucket
        self._image_quality_in_editor = image_quality_in_editor
        self._s3_repo = s3_repo
        self._service_provider = service_provider
        self._annotation_status = annotation_status
        self._auth_data = None

    @property
    def s3_repo(self):
        self._auth_data = self._service_provider.get_s3_upload_auth_token(
            self._project, self._folder
        )
        if not self._auth_data.ok:
            raise AppException(self._auth_data.data.get("error"))
        return self._s3_repo(
            self._auth_data.data["accessKeyId"],
            self._auth_data.data["secretAccessKey"],
            self._auth_data.data["sessionToken"],
            self._auth_data.data["bucket"],
            self._auth_data.data["region"],
        )

    def validate_project_type(self):
        if self._project.upload_state == constances.UploadState.EXTERNAL.value:
            raise AppValidationException(constances.UPLOADING_UPLOAD_STATE_ERROR)

    def validate_deprecation(self):
        if self._project.type in [
            constances.ProjectType.VIDEO.value,
            constances.ProjectType.DOCUMENT.value,
        ]:
            raise AppException(constances.LIMITED_FUNCTIONS[self._project.type])

    def validate_limitations(self):
        response = self._service_provider.get_limitations(self._project, self._folder)
        if response.data.folder_limit.remaining_image_count < 1:
            raise AppValidationException(constances.UPLOAD_FOLDER_LIMIT_ERROR_MESSAGE)
        elif response.data.project_limit.remaining_image_count < 1:
            raise AppValidationException(constances.UPLOAD_PROJECT_LIMIT_ERROR_MESSAGE)
        elif (
            response.data.user_limit
            and response.data.user_limit.remaining_image_count < 1
        ):
            raise AppValidationException(constances.UPLOAD_USER_LIMIT_ERROR_MESSAGE)

    @property
    def auth_data(self):
        return self._auth_data

    def validate_arguments(self):
        if not self._image_path and self._image_bytes is None:
            raise AppValidationException("Image data not provided.")

    def validate_image_name_uniqueness(self):
        image_entities = self._service_provider.items.list_by_names(
            project=self._project,
            folder=self._folder,
            names=[
                self._image_name if self._image_name else Path(self._image_path).name
            ],
        ).data
        if image_entities:
            raise AppValidationException("Image with this name already exists.")

    def execute(self) -> Response:
        if self.is_valid():
            if self._image_path and self._from_s3_bucket:
                image_bytes = (
                    GetS3ImageUseCase(
                        s3_bucket=self._from_s3_bucket, image_path=self._image_path
                    )
                    .execute()
                    .data
                )
            elif self._image_path:
                image_bytes = io.BytesIO(open(self._image_path, "rb").read())
            else:
                image_bytes = self._image_bytes

            s3_upload_response = UploadImageS3UseCase(
                project=self._project,
                image_path=self._image_name
                if self._image_name
                else Path(self._image_path).name,
                service_provider=self._service_provider,
                image=image_bytes,
                s3_repo=self.s3_repo,
                upload_path=self.auth_data.data["filePath"],
                image_quality_in_editor=self._image_quality_in_editor,
            ).execute()

            if s3_upload_response.errors:
                raise AppException(s3_upload_response.errors)
            AttachFileUrlsUseCase(
                project=self._project,
                folder=self._folder,
                attachments=[s3_upload_response.data],
                service_provider=self._service_provider,
                annotation_status=self._annotation_status,
                upload_state_code=constances.UploadState.BASIC.value,
            ).execute()
        return self._response


class UploadImagesToProject(BaseInteractiveUseCase):
    MAX_WORKERS = 10
    LIST_NAME_CHUNK_SIZE = 500

    def __init__(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        s3_repo,
        service_provider: BaseServiceProvider,
        paths: List[str],
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
        self._paths = paths
        self._project = project
        self._folder = folder
        self._service_provider = service_provider
        self._s3_repo = s3_repo
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

    def validate_limitations(self):
        response = self._service_provider.get_limitations(self._project, self._folder)
        if not response.ok:
            raise AppValidationException(response.error)
        to_upload_count = len(self.images_to_upload[0])
        if to_upload_count > response.data.folder_limit.remaining_image_count:
            raise AppValidationException(constances.UPLOAD_FOLDER_LIMIT_ERROR_MESSAGE)
        elif to_upload_count > response.data.project_limit.remaining_image_count:
            raise AppValidationException(constances.UPLOAD_PROJECT_LIMIT_ERROR_MESSAGE)
        elif (
            response.data.user_limit
            and to_upload_count > response.data.user_limit.remaining_image_count
        ):
            raise AppValidationException(constances.UPLOAD_USER_LIMIT_ERROR_MESSAGE)

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
        if self._project.upload_state == constances.UploadState.EXTERNAL.value:
            raise AppValidationException(constances.UPLOADING_UPLOAD_STATE_ERROR)

    def validate_deprecation(self):
        if self._project.type in constances.LIMITED_FUNCTIONS:
            raise AppValidationException(
                constances.LIMITED_FUNCTIONS[self._project.type]
            )

    @property
    def auth_data(self):
        if not self._auth_data:
            response = self._service_provider.get_s3_upload_auth_token(
                project=self._project, folder=self._folder
            )
            if not response.ok:
                raise AppException(response.error)
            self._auth_data = response.data
        return self._auth_data

    @property
    def s3_repository(self):
        if not self._s3_repo_instance:
            self._s3_repo_instance = self._s3_repo(
                self.auth_data["accessKeyId"],
                self.auth_data["secretAccessKey"],
                self.auth_data["sessionToken"],
                self.auth_data["bucket"],
                self.auth_data["region"],
            )
        return self._s3_repo_instance

    def _upload_image(self, image_path: str):
        ProcessedImage = namedtuple(
            "ProcessedImage", ["uploaded", "path", "entity", "name"]
        )
        if self._from_s3_bucket:
            response = GetS3ImageUseCase(
                s3_bucket=self._from_s3_bucket, image_path=image_path
            ).execute()
            if response.errors:
                logger.warning(
                    f"Unable to upload image {image_path} \n{response.errors}"
                )
                return ProcessedImage(
                    uploaded=False,
                    path=image_path,
                    entity=None,
                    name=Path(image_path).name,
                )
            image_bytes = response.data
        else:
            try:
                image_bytes = io.BytesIO(open(image_path, "rb").read())
            except OSError:
                return ProcessedImage(
                    uploaded=False,
                    path=image_path,
                    entity=None,
                    name=Path(image_path).name,
                )
        upload_response = UploadImageS3UseCase(
            project=self._project,
            image_path=image_path,
            image=image_bytes,
            s3_repo=self.s3_repository,
            upload_path=self.auth_data["filePath"],
            service_provider=self._service_provider,
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

    def filter_paths(self, paths: List[str]):
        paths = [
            path
            for path in paths
            if not any([extension in path for extension in self.exclude_file_patterns])
        ]
        name_path_map = defaultdict(list)
        for path in paths:
            name_path_map[Path(path).name].append(path)

        CHUNK_SIZE = UploadImagesToProject.LIST_NAME_CHUNK_SIZE

        filtered_paths = []
        duplicated_paths = []
        existing_items = []
        for file_name in name_path_map:
            if len(name_path_map[file_name]) > 1:
                duplicated_paths.extend(name_path_map[file_name][1:])
            filtered_paths.append(name_path_map[file_name][0])

        if duplicated_paths:
            logger.warning(
                f"{len(duplicated_paths)} duplicate paths found that won't be uploaded."
            )

        image_list = []
        for i in range(0, len(filtered_paths), CHUNK_SIZE):
            response = self._service_provider.items.list_by_names(
                project=self._project,
                folder=self._folder,
                names=[
                    image.split("/")[-1] for image in filtered_paths[i : i + CHUNK_SIZE]
                ],
            )

            if not response.ok:
                raise AppException(response.error)
            image_list.extend([image.name for image in response.data])

        image_list = set(image_list)
        images_to_upload = []

        for path in filtered_paths:
            image_name = Path(path).name
            if image_name not in image_list:
                images_to_upload.append(path)
            else:
                existing_items.append(image_name)
        return list(set(images_to_upload)), existing_items

    @property
    def images_to_upload(self):
        if not self._images_to_upload:
            self._images_to_upload = self.filter_paths(self._paths)
        return self._images_to_upload

    def execute(self):
        if self.is_valid():
            images_to_upload, existing_items = self.images_to_upload
            images_to_upload = images_to_upload[: self.auth_data["availableImageCount"]]
            if not images_to_upload:
                return self._response

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
            attach_duplications_list = []
            for i in range(0, len(uploaded_images), 100):
                response = AttachFileUrlsUseCase(
                    project=self._project,
                    folder=self._folder,
                    service_provider=self._service_provider,
                    attachments=[
                        image.entity
                        for image in uploaded_images[i : i + 100]  # noqa: E203
                    ],
                    annotation_status=self._annotation_status,
                    upload_state_code=constances.UploadState.BASIC.value,
                ).execute()
                if response.errors:
                    logger.error(response.errors)
                    continue
                attachments, attach_duplications = response.data
                uploaded.extend(attachments)
                attach_duplications_list.extend(attach_duplications)
            if attach_duplications_list:
                logger.debug(
                    f"{len(attach_duplications_list)} item attachments duplicates found."
                )
            uploaded = [image["name"] for image in uploaded]
            failed_images = [image.split("/")[-1] for image in failed_images]
            self._response.data = uploaded, failed_images, existing_items
        return self._response


class UploadImagesFromFolderToProject(UploadImagesToProject):
    MAX_WORKERS = 10

    def __init__(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        s3_repo,
        service_provider: BaseServiceProvider,
        folder_path: str,
        extensions=constances.DEFAULT_IMAGE_EXTENSIONS,
        annotation_status="NotStarted",
        from_s3_bucket=None,
        exclude_file_patterns: List[str] = constances.DEFAULT_FILE_EXCLUDE_PATTERNS,
        recursive_sub_folders: bool = False,
        image_quality_in_editor=None,
    ):
        paths = UploadImagesFromFolderToProject.extract_paths(
            folder_path=folder_path,
            extensions=extensions,
            from_s3_bucket=from_s3_bucket,
            recursive_sub_folders=recursive_sub_folders,
        )
        super().__init__(
            project=project,
            folder=folder,
            s3_repo=s3_repo,
            service_provider=service_provider,
            paths=paths,
            extensions=extensions,
            annotation_status=annotation_status,
            from_s3_bucket=from_s3_bucket,
            exclude_file_patterns=exclude_file_patterns,
            recursive_sub_folders=recursive_sub_folders,
            image_quality_in_editor=image_quality_in_editor,
        )

    @classmethod
    def extract_paths(
        cls, folder_path, extensions, from_s3_bucket=None, recursive_sub_folders=False
    ):
        if not extensions:
            extensions = constances.DEFAULT_IMAGE_EXTENSIONS
        paths = []
        if from_s3_bucket is None:
            for extension in extensions:
                if recursive_sub_folders:
                    paths += list(Path(folder_path).rglob(f"*.{extension.lower()}"))
                    if os.name != "nt":
                        paths += list(Path(folder_path).rglob(f"*.{extension.upper()}"))
                else:
                    paths += list(Path(folder_path).glob(f"*.{extension.lower()}"))
                    if os.name != "nt":
                        paths += list(Path(folder_path).glob(f"*.{extension.upper()}"))

        else:
            s3_client = boto3.client("s3")
            paginator = s3_client.get_paginator("list_objects_v2")
            response_iterator = paginator.paginate(
                Bucket=from_s3_bucket, Prefix=folder_path
            )
            for response in response_iterator:
                contents = response.get("Contents", [])
                for object_data in contents:
                    key = object_data["Key"]
                    if not recursive_sub_folders and "/" in key[len(folder_path) + 1 :]:
                        continue
                    for extension in extensions:
                        if key.endswith(f".{extension.lower()}") or key.endswith(
                            f".{extension.upper()}"
                        ):
                            paths.append(key)
                            break

        return [str(path) for path in paths]


class UploadImageS3UseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        image_path: str,
        image: io.BytesIO,
        s3_repo: BaseManageableRepository,
        upload_path: str,
        service_provider: BaseServiceProvider,
        image_quality_in_editor: str = None,
    ):
        super().__init__()
        self._project = project
        self._image_path = image_path
        self._image = image
        self._s3_repo = s3_repo
        self._upload_path = upload_path
        self._service_provider = service_provider
        self._image_quality_in_editor = image_quality_in_editor

    @property
    def max_resolution(self) -> int:
        if self._project.type == ProjectType.PIXEL.value:
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
                _response = self._service_provider.projects.list_settings(self._project)
                if not _response.ok:
                    self._response.errors = AppException(_response.error)
                    return self._response
                for setting in _response.data:
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
                meta=dict(width=origin_width, height=origin_height),
            )
        except (ImageProcessingException, UnidentifiedImageError) as e:
            self._response.errors = e
        return self._response


class DeleteAnnotations(BaseUseCase):
    POLL_AWAIT_TIME = 2
    CHUNK_SIZE = 2000

    def __init__(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        service_provider: BaseServiceProvider,
        image_names: Optional[List[str]] = None,
    ):
        super().__init__()
        self._project = project
        self._folder = folder
        self._image_names = image_names
        self._service_provider = service_provider

    def execute(self) -> Response:
        polling_states = {}
        if self._image_names:
            for idx in range(0, len(self._image_names), self.CHUNK_SIZE):
                response = self._service_provider.annotations.delete(
                    project=self._project,
                    folder=self._folder,
                    item_names=self._image_names[
                        idx : idx + self.CHUNK_SIZE  # noqa: E203
                    ],
                )
                if response.ok:
                    polling_states[response.data.get("poll_id")] = False
        else:
            response = self._service_provider.annotations.delete(
                project=self._project,
                folder=self._folder,
            )
            if response.ok:
                polling_states[response.data.get("poll_id")] = False

        if not polling_states:
            self._response.errors = AppException("Invalid item names or empty folder.")
        else:
            for poll_id in polling_states:
                timeout_start = time.time()
                while time.time() < timeout_start + self.POLL_AWAIT_TIME:
                    progress = int(
                        self._service_provider.annotations.get_delete_progress(
                            project=self._project,
                            poll_id=poll_id,
                        ).data.get("process", -1)
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


class DownloadImageAnnotationsUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        image_name: str,
        service_provider: BaseServiceProvider,
        destination: str,
    ):
        super().__init__()
        self._project = project
        self._folder = folder
        self._image_name = image_name
        self._service_provider = service_provider
        self._destination = destination

    @property
    def image_use_case(self):
        return GetImageUseCase(
            service_provider=self._service_provider,
            project=self._project,
            folder=self._folder,
            image_name=self._image_name,
        )

    def validate_project_type(self):
        if self._project.type in constances.LIMITED_FUNCTIONS:
            raise AppValidationException(
                constances.LIMITED_FUNCTIONS[self._project.type]
            )

    @property
    def annotation_classes_id_name_map(self) -> dict:
        classes_data = defaultdict(dict)
        annotation_classes = self._service_provider.annotation_classes.list(
            Condition("project_id", self._project.id, EQ)
        ).data
        for annotation_class in annotation_classes:
            class_info = {"name": annotation_class.name, "attribute_groups": {}}
            if annotation_class.attribute_groups:
                for attribute_group in annotation_class.attribute_groups:
                    attribute_group_data = defaultdict(dict)
                    for attribute in attribute_group.attributes:
                        attribute_group_data[attribute.id] = attribute.name
                    class_info["attribute_groups"] = {
                        attribute_group.id: {
                            "name": attribute_group.name,
                            "attributes": attribute_group_data,
                        }
                    }
            classes_data[annotation_class.id] = class_info
        return classes_data

    def get_templates_mapping(self):
        templates = self._service_provider.list_templates().data["data"]
        templates_map = {}
        for template in templates:
            templates_map[template["id"]] = template["name"]
        return templates_map

    def fill_classes_data(self, annotations: dict):
        annotation_classes = self.annotation_classes_id_name_map
        if "instances" not in annotations:
            return
        templates = self.get_templates_mapping()
        for annotation in (
            i for i in annotations["instances"] if i.get("type", None) == "template"
        ):
            template_name = templates.get(annotation.get("templateId"), None)
            if template_name:
                annotation["templateName"] = template_name
        for annotation in [
            i
            for i in annotations["instances"]
            if "classId" in i and i["classId"] in annotation_classes
        ]:
            annotation_class = annotation_classes[annotation["classId"]]
            annotation["className"] = annotation_class["name"]
            for attribute in [
                i
                for i in annotation.get("attributes", [])
                if "groupId" in i
                and i["groupId"] in annotation_class["attribute_groups"].keys()
            ]:
                attribute["groupName"] = annotation_class["attribute_groups"][
                    attribute["groupId"]
                ]["name"]
                if attribute.get("id") in list(
                    annotation_class["attribute_groups"][attribute["groupId"]][
                        "attributes"
                    ].keys()
                ):
                    attribute["name"] = annotation_class["attribute_groups"][
                        attribute["groupId"]
                    ]["attributes"][attribute["id"]]

    def execute(self):
        if self.is_valid():
            data = {
                "annotation_json": None,
                "annotation_json_filename": None,
                "annotation_mask": None,
                "annotation_mask_filename": None,
            }
            image_response = self.image_use_case.execute()
            token = self._service_provider.get_download_token(
                project=self._project,
                folder=self._folder,
                image_id=image_response.data.id,
            ).data
            credentials = token["annotations"]["MAIN"][0]

            annotation_json_creds = credentials["annotation_json_path"]

            response = requests.get(
                url=annotation_json_creds["url"],
                headers=annotation_json_creds["headers"],
            )
            if not response.ok:
                # TODO remove
                logger.warning("Couldn't load annotations.")
                self._response.data = (None, None)
                return self._response
            data["annotation_json"] = response.json()
            data["annotation_json_filename"] = f"{self._image_name}.json"
            mask_path = None
            if self._project.type == constances.ProjectType.PIXEL.value:
                annotation_blue_map_creds = credentials["annotation_bluemap_path"]
                response = requests.get(
                    url=annotation_blue_map_creds["url"],
                    headers=annotation_blue_map_creds["headers"],
                )
                data["annotation_mask_filename"] = f"{self._image_name}___save.png"
                if response.ok:
                    data["annotation_mask"] = io.BytesIO(response.content).getbuffer()
                    mask_path = (
                        Path(self._destination) / data["annotation_mask_filename"]
                    )
                    with open(mask_path, "wb") as f:
                        f.write(data["annotation_mask"])
                else:
                    logger.info("There is no blue-map for the image.")

            json_path = Path(self._destination) / data["annotation_json_filename"]
            self.fill_classes_data(data["annotation_json"])
            with open(json_path, "w") as f:
                json.dump(data["annotation_json"], f, indent=4)

            self._response.data = (str(json_path), str(mask_path))
        return self._response


class UnAssignFolderUseCase(BaseUseCase):
    def __init__(
        self,
        service_provider: BaseServiceProvider,
        project: ProjectEntity,
        folder: FolderEntity,
    ):
        super().__init__()
        self._service_provider = service_provider
        self._project = project
        self._folder = folder

    def execute(self):
        is_un_assigned = self._service_provider.folders.un_assign_all(
            project=self._project, folder=self._folder
        ).ok
        if not is_un_assigned:
            self._response.errors = AppException(f"Cant un assign {self._folder.name}")
        return self._response


class DeleteAnnotationClassUseCase(BaseUseCase):
    def __init__(
        self,
        annotation_class: AnnotationClassEntity,
        project: ProjectEntity,
        service_provider: BaseServiceProvider,
    ):
        super().__init__()
        self._service_provider = service_provider
        self._name = annotation_class.name
        self._project = project

    def execute(self):
        annotation_classes = self._service_provider.annotation_classes.list(
            condition=Condition("name", self._name, EQ)
            & Condition("pattern", True, EQ)
            & Condition("project_id", self._project.id, EQ)
        ).data
        if annotation_classes:
            annotation_class = annotation_classes[0]
            logger.info(
                "Deleting annotation class from project %s with name %s",
                self._project.name,
                self._name,
            )
            self._service_provider.annotation_classes.delete(
                project_id=self._project.id, annotation_class_id=annotation_class.id
            )
        return self._response


class ExtractFramesUseCase(BaseInteractiveUseCase):
    def __init__(
        self,
        service_provider: BaseServiceProvider,
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
        self._service_provider = service_provider
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
        self._limitation_response = None

    def validate_fps(self):
        fps = VideoPlugin.get_fps(self._video_path)
        if not self._target_fps:
            self._target_fps = fps
            return
        if self._target_fps and self._target_fps > fps:
            logger.info(
                f"Video frame rate {fps} smaller than target frame rate {self._target_fps}. Cannot change frame rate."
            )
        else:
            logger.info(
                f"Changing video frame rate from {fps} to target frame rate {self._target_fps}."
            )

    def validate_upload_state(self):
        if self._project.upload_state == constances.UploadState.EXTERNAL.value:
            raise AppValidationException(constances.UPLOADING_UPLOAD_STATE_ERROR)

    @property
    def limitation_response(self):
        if not self._limitation_response:
            self._limitation_response = self._service_provider.get_limitations(
                self._project, self._folder
            )
            if not self._limitation_response.ok:
                raise AppValidationException(self._limitation_response.error)
        return self._limitation_response

    def validate_limitations(self):
        response = self.limitation_response
        if not response.ok:
            raise AppValidationException(response.error)
        if not response.data.folder_limit.remaining_image_count:
            raise AppValidationException(constances.UPLOAD_FOLDER_LIMIT_ERROR_MESSAGE)
        elif not response.data.project_limit.remaining_image_count:
            raise AppValidationException(constances.UPLOAD_PROJECT_LIMIT_ERROR_MESSAGE)
        elif (
            response.data.user_limit
            and response.data.user_limit.remaining_image_count < 1
        ):
            raise AppValidationException(constances.UPLOAD_USER_LIMIT_ERROR_MESSAGE)

    @property
    def limit(self):
        limits = [
            self.limitation_response.data.folder_limit.remaining_image_count,
            self.limitation_response.data.project_limit.remaining_image_count,
        ]
        if self.limitation_response.data.user_limit:
            limits.append(
                self.limitation_response.data.user_limit.remaining_image_count
            )
        return min(limits)

    def validate_project_type(self):
        if self._project.type in constances.LIMITED_FUNCTIONS:
            raise AppValidationException(
                constances.LIMITED_FUNCTIONS[self._project.type]
            )

    def execute(self):
        if self.is_valid():
            frames_generator = VideoPlugin.extract_frames(
                video_path=self._video_path,
                start_time=self._start_time,
                end_time=self._end_time,
                extract_path=self._extract_path,
                limit=self.limit,
                target_fps=self._target_fps,
            )
            yield from frames_generator


class UploadVideosAsImages(BaseReportableUseCase):
    def __init__(
        self,
        reporter: Reporter,
        service_provider: BaseServiceProvider,
        project: ProjectEntity,
        folder: FolderEntity,
        s3_repo,
        paths: List[str],
        target_fps: int,
        extensions: List[str] = constances.DEFAULT_VIDEO_EXTENSIONS,
        exclude_file_patterns: List[str] = (),
        start_time: Optional[float] = 0.0,
        end_time: Optional[float] = None,
        annotation_status: str = constances.AnnotationStatus.NOT_STARTED,
        image_quality_in_editor=None,
    ):
        super().__init__(reporter)
        self._service_provider = service_provider
        self._project = project
        self._folder = folder
        self._s3_repo = s3_repo
        self._paths = paths
        self._target_fps = target_fps
        self._extensions = extensions
        self._exclude_file_patterns = exclude_file_patterns
        self._start_time = start_time
        self._end_time = end_time
        self._annotation_status = annotation_status
        self._image_quality_in_editor = image_quality_in_editor

    @property
    def annotation_status(self):
        if not self._annotation_status:
            return constances.AnnotationStatus.NOT_STARTED.name
        return self._annotation_status

    @property
    def upload_path(self):
        if self._folder.name != "root":
            return f"{self._project.name}/{self._folder.name}"
        return self._project.name

    @property
    def exclude_file_patterns(self):
        if not self._exclude_file_patterns:
            return []
        return self._exclude_file_patterns

    @property
    def extensions(self):
        if not self._extensions:
            return constances.DEFAULT_VIDEO_EXTENSIONS
        return self._extensions

    def validate_project_type(self):
        if self._project.type in constances.LIMITED_FUNCTIONS:
            raise AppValidationException(
                constances.LIMITED_FUNCTIONS[self._project.type]
            )

    def validate_paths(self):
        validated_paths = set()
        for path in self._paths:
            path = Path(path)
            if (
                path.exists()
                and path.name not in self.exclude_file_patterns
                and path.suffix.split(".")[-1] in self.extensions
            ):
                validated_paths.add(path)
        if not validated_paths:
            raise AppValidationException("There is no valid path.")

        self._paths = list(validated_paths)

    def execute(self) -> Response:
        if self.is_valid():
            data = []
            for path in self._paths:
                with tempfile.TemporaryDirectory() as temp_path:
                    frame_names = VideoPlugin.get_extractable_frames(
                        path, self._start_time, self._end_time, self._target_fps
                    )
                    duplicate_images = self._service_provider.items.list_by_names(
                        project=self._project, folder=self._folder, names=frame_names
                    ).data

                    duplicate_images = [image.name for image in duplicate_images]
                    frames_generator_use_case = ExtractFramesUseCase(
                        service_provider=self._service_provider,
                        project=self._project,
                        folder=self._folder,
                        video_path=path,
                        extract_path=temp_path,
                        start_time=self._start_time,
                        end_time=self._end_time,
                        target_fps=self._target_fps,
                        annotation_status_code=self.annotation_status,
                        image_quality_in_editor=self._image_quality_in_editor,
                    )
                    if not frames_generator_use_case.is_valid():
                        self._response.errors = (
                            frames_generator_use_case.response.errors
                        )
                        return self._response

                    frames_generator = frames_generator_use_case.execute()

                    total_frames_count = len(frame_names)
                    self.reporter.log_info(
                        f"Video frame count is {total_frames_count}."
                    )
                    self.reporter.log_info(
                        f"Extracted {total_frames_count} frames from video. Now uploading to platform.",
                    )
                    self.reporter.log_info(
                        f"Uploading {total_frames_count} images to project {str(self.upload_path)}."
                    )
                    if len(duplicate_images):
                        self.reporter.log_warning(
                            f"{len(duplicate_images)} already existing images found that won't be uploaded."
                        )
                    if set(duplicate_images) == set(frame_names):
                        continue
                    uploaded_paths = []
                    with Progress(
                        total_frames_count, f"Uploading {Path(path).name}"
                    ) as progress:
                        for _ in frames_generator:
                            use_case = UploadImagesFromFolderToProject(
                                project=self._project,
                                folder=self._folder,
                                service_provider=self._service_provider,
                                folder_path=temp_path,
                                s3_repo=self._s3_repo,
                                annotation_status=self.annotation_status,
                                image_quality_in_editor=self._image_quality_in_editor,
                            )

                            images_to_upload, duplicates = use_case.images_to_upload
                            if not len(images_to_upload):
                                continue
                            if use_case.is_valid():
                                for _ in use_case.execute():
                                    progress.update()

                                uploaded, failed_images, _ = use_case.response.data
                                uploaded_paths.extend(uploaded)
                                if failed_images:
                                    self.reporter.log_warning(
                                        f"Failed {len(failed_images)}."
                                    )
                                files = os.listdir(temp_path)
                                image_paths = [f"{temp_path}/{f}" for f in files]
                                for image_path in image_paths:
                                    os.remove(image_path)
                            else:
                                raise AppException(use_case.response.errors)
                data.extend(uploaded_paths)
            self._response.data = data
        return self._response
