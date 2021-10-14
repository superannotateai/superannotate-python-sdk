import concurrent.futures
import copy
import io
import json
import logging
import os.path
import random
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
from lib.core.entities import FolderEntity
from lib.core.entities import ImageEntity
from lib.core.entities import ImageInfoEntity
from lib.core.entities import ProjectEntity
from lib.core.entities import ProjectSettingEntity
from lib.core.entities import S3FileEntity
from lib.core.enums import ImageQuality
from lib.core.enums import ProjectType
from lib.core.exceptions import AppException
from lib.core.exceptions import AppValidationException
from lib.core.exceptions import ImageProcessingException
from lib.core.helpers import fill_annotation_ids
from lib.core.helpers import map_annotation_classes_name
from lib.core.plugin import ImagePlugin
from lib.core.plugin import VideoPlugin
from lib.core.repositories import BaseManageableRepository
from lib.core.repositories import BaseReadOnlyRepository
from lib.core.response import Response
from lib.core.serviceproviders import SuerannotateServiceProvider
from lib.core.types import PixelAnnotation
from lib.core.types import VectorAnnotation
from lib.core.usecases.base import BaseInteractiveUseCase
from lib.core.usecases.base import BaseUseCase
from lib.core.usecases.projects import GetAnnotationClassesUseCase
from PIL import UnidentifiedImageError
from pydantic import ValidationError

logger = logging.getLogger("root")


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

    def validate_project_type(self):
        if self._project.project_type in constances.LIMITED_FUNCTIONS:
            raise AppValidationException(
                constances.LIMITED_FUNCTIONS[self._project.project_type]
            )

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
            response = self._service.get_bulk_images(
                project_id=self._project_id,
                team_id=self._team_id,
                folder_id=self._folder_id,
                images=self._images[i : i + self._chunk_size],  # noqa: E203
            )
            if "error" in response:
                raise AppException(response["error"])
            res += [ImageEntity.from_dict(**image) for image in response]
        self._response.data = res
        return self._response


class AttachFileUrlsUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        attachments: List[ImageEntity],
        backend_service_provider: SuerannotateServiceProvider,
        annotation_status: str = None,
        upload_state_code: int = constances.UploadState.EXTERNAL.value,
    ):
        super().__init__()
        self._attachments = attachments
        self._project = project
        self._folder = folder
        self._backend_service = backend_service_provider
        self._annotation_status = annotation_status
        self._upload_state_code = upload_state_code

    def _validate_limitations(self, to_upload_count):
        response = self._backend_service.get_limitations(
            team_id=self._project.team_id,
            project_id=self._project.uuid,
            folder_id=self._folder.uuid,
        )
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
        try:
            self._validate_limitations(len(to_upload))
        except AppValidationException as e:
            self._response.errors = e
            return self._response
        if to_upload:
            backend_response = self._backend_service.attach_files(
                project_id=self._project.uuid,
                folder_id=self._folder.uuid,
                team_id=self._project.team_id,
                files=to_upload,
                annotation_status_code=self.annotation_status_code,
                upload_state_code=self.upload_state_code,
                meta=meta,
            )
            if isinstance(backend_response, dict) and "error" in backend_response:
                self._response.errors = AppException(backend_response["error"])
            else:
                self._response.data = backend_response, duplications
        else:
            self._response.data = [], duplications
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

    def _validate_limitations(self, images_to_copy_count):
        response = self._backend_service.get_limitations(
            team_id=self._project.team_id,
            project_id=self._project.uuid,
            folder_id=self._to_folder.uuid,
        )
        if not response.ok:
            raise AppValidationException(response.error)
        if images_to_copy_count > response.data.folder_limit.remaining_image_count:
            raise AppValidationException(constances.COPY_FOLDER_LIMIT_ERROR_MESSAGE)
        if images_to_copy_count > response.data.project_limit.remaining_image_count:
            raise AppValidationException(constances.COPY_PROJECT_LIMIT_ERROR_MESSAGE)

    def validate_project_type(self):
        if self._project.project_type in constances.LIMITED_FUNCTIONS:
            raise AppValidationException(
                constances.LIMITED_FUNCTIONS[self._project.project_type]
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
            try:
                self._validate_limitations(len(images_to_copy))
            except AppValidationException as e:
                self._response.errors = e
                return self._response

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
        if self._project.project_type in constances.LIMITED_FUNCTIONS:
            raise AppValidationException(
                constances.LIMITED_FUNCTIONS[self._project.project_type]
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

    def validate_limitations(self):
        response = self._backend_service.get_limitations(
            team_id=self._project.team_id,
            project_id=self._project.uuid,
            folder_id=self._to_folder.uuid,
        )
        to_upload_count = len(self._image_names)
        if not response.ok:
            raise AppValidationException(response.error)
        if to_upload_count > response.data.folder_limit.remaining_image_count:
            raise AppValidationException(constances.MOVE_FOLDER_LIMIT_ERROR_MESSAGE)
        if to_upload_count > response.data.project_limit.remaining_image_count:
            raise AppValidationException(constances.MOVE_PROJECT_LIMIT_ERROR_MESSAGE)

    def execute(self):
        if self.is_valid():
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
        self, s3_bucket, image_path: str,
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


class DownloadImageUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        image: ImageEntity,
        images: BaseManageableRepository,
        classes: BaseManageableRepository,
        backend_service_provider: SuerannotateServiceProvider,
        annotation_classes: BaseReadOnlyRepository,
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
            annotation_classes=annotation_classes,
        )
        self.get_annotation_classes_ues_case = GetAnnotationClassesUseCase(
            classes=classes,
        )

    def validate_project_type(self):
        if self._project.project_type in constances.LIMITED_FUNCTIONS:
            raise AppValidationException(
                constances.LIMITED_FUNCTIONS[self._project.project_type]
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
                classes = self.get_annotation_classes_ues_case.execute().data
                fuse_image = (
                    CreateFuseImageUseCase(
                        project_type=constances.ProjectType.get_name(
                            self._project.project_type
                        ),
                        image_path=download_path,
                        classes=[
                            annotation_class.to_dict() for annotation_class in classes
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
        settings: BaseManageableRepository,
        backend_client: SuerannotateServiceProvider,
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
        self._settings = settings
        self._s3_repo = s3_repo
        self._backend_client = backend_client
        self._annotation_status = annotation_status
        self._auth_data = None

    @property
    def s3_repo(self):
        self._auth_data = self._backend_client.get_s3_upload_auth_token(
            self._project.team_id, self._folder.uuid, self._project.uuid
        )
        if "error" in self._auth_data:
            raise AppException(self._auth_data.get("error"))
        return self._s3_repo(
            self._auth_data["accessKeyId"],
            self._auth_data["secretAccessKey"],
            self._auth_data["sessionToken"],
            self._auth_data["bucket"],
        )

    def validate_project_type(self):
        if self._project.upload_state == constances.UploadState.EXTERNAL.value:
            raise AppValidationException(constances.UPLOADING_UPLOAD_STATE_ERROR)

    def validate_deprecation(self):
        if self._project.project_type in [
            constances.ProjectType.VIDEO.value,
            constances.ProjectType.DOCUMENT.value,
        ]:
            raise AppException(constances.LIMITED_FUNCTIONS[self._project.project_type])

    def validate_limitations(self):
        response = self._backend_client.get_limitations(
            team_id=self._project.team_id,
            project_id=self._project.uuid,
            folder_id=self._folder.uuid,
        )
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
        image_entities = (
            GetBulkImages(
                service=self._backend_client,
                project_id=self._project.uuid,
                team_id=self._project.team_id,
                folder_id=self._folder.uuid,
                images=[
                    self._image_name
                    if self._image_name
                    else Path(self._image_path).name
                ],
            )
            .execute()
            .data
        )
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
                project_settings=self._settings.get_all(),
                image=image_bytes,
                s3_repo=self.s3_repo,
                upload_path=self.auth_data["filePath"],
                image_quality_in_editor=self._image_quality_in_editor,
            ).execute()

            if s3_upload_response.errors:
                raise AppException(s3_upload_response.errors)
            AttachFileUrlsUseCase(
                project=self._project,
                folder=self._folder,
                attachments=[s3_upload_response.data],
                backend_service_provider=self._backend_client,
                annotation_status=self._annotation_status,
                upload_state_code=constances.UploadState.BASIC.value,
            ).execute()
        return self._response


class UploadImagesToProject(BaseInteractiveUseCase):
    MAX_WORKERS = 10

    def __init__(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        settings: BaseManageableRepository,
        s3_repo,
        backend_client: SuerannotateServiceProvider,
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

    def validate_limitations(self):
        response = self._backend_client.get_limitations(
            team_id=self._project.team_id,
            project_id=self._project.uuid,
            folder_id=self._folder.uuid,
        )
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
        if self._project.project_type in constances.LIMITED_FUNCTIONS:
            raise AppValidationException(
                constances.LIMITED_FUNCTIONS[self._project.project_type]
            )

    @property
    def auth_data(self):
        if not self._auth_data:
            response = self._backend_client.get_s3_upload_auth_token(
                team_id=self._project.team_id,
                folder_id=self._folder.uuid,
                project_id=self._project.uuid,
            )
            if "error" in response:
                raise AppException(response.get("error"))
            self._auth_data = response
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

    def filter_paths(self, paths: List[str]):
        paths = [
            path
            for path in paths
            if not any([extension in path for extension in self.exclude_file_patterns])
        ]
        name_path_map = defaultdict(list)
        for path in paths:
            name_path_map[Path(path).name].append(path)

        filtered_paths = []
        duplicated_paths = []
        for file_name in name_path_map:
            if len(name_path_map[file_name]) > 1:
                duplicated_paths.append(name_path_map[file_name][1:])
            filtered_paths.append(name_path_map[file_name][0])

        image_entities = (
            GetBulkImages(
                service=self._backend_client,
                project_id=self._project.uuid,
                team_id=self._project.team_id,
                folder_id=self._folder.uuid,
                images=[image.split("/")[-1] for image in filtered_paths],
            )
            .execute()
            .data
        )
        images_to_upload = []
        image_list = [image.name for image in image_entities]

        for path in filtered_paths:
            if Path(path).name not in image_list:
                images_to_upload.append(path)
            else:
                duplicated_paths.append(path)
        return list(set(images_to_upload)), duplicated_paths

    @property
    def images_to_upload(self):
        if not self._images_to_upload:
            self._images_to_upload = self.filter_paths(self._paths)
        return self._images_to_upload

    def execute(self):
        if self.is_valid():
            images_to_upload, duplications = self.images_to_upload
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
            for i in range(0, len(uploaded_images), 100):
                response = AttachFileUrlsUseCase(
                    project=self._project,
                    folder=self._folder,
                    backend_service_provider=self._backend_client,
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
                duplications.extend(attach_duplications)
            uploaded = [image["name"] for image in uploaded]
            failed_images = [image.split("/")[-1] for image in failed_images]
            self._response.data = uploaded, failed_images, duplications
        return self._response


class UploadImagesFromFolderToProject(UploadImagesToProject):
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
        paths = UploadImagesFromFolderToProject.extract_paths(
            folder_path=folder_path,
            extensions=extensions,
            from_s3_bucket=from_s3_bucket,
            recursive_sub_folders=recursive_sub_folders,
        )
        super().__init__(
            project,
            folder,
            settings,
            s3_repo,
            backend_client,
            paths,
            extensions,
            annotation_status,
            from_s3_bucket,
            exclude_file_patterns,
            recursive_sub_folders,
            image_quality_in_editor,
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


class UploadImagesFromPublicUrls(BaseInteractiveUseCase):
    MAX_WORKERS = 10
    ProcessedImage = namedtuple("ProcessedImage", ["url", "uploaded", "path", "entity"])

    def __init__(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        backend_service: SuerannotateServiceProvider,
        settings: BaseManageableRepository,
        s3_repo,
        image_urls: List[str],
        image_names: List[str] = None,
        annotation_status: str = None,
        image_quality_in_editor: str = None,
    ):
        super().__init__()
        self._project = project
        self._folder = folder
        self._backend_service = backend_service
        self._s3_repo = s3_repo
        self._image_urls = image_urls
        self._image_names = image_names
        self._annotation_status = annotation_status
        self._image_quality_in_editor = image_quality_in_editor
        self._settings = settings
        self._auth_data = None

    @property
    def auth_data(self):
        if not self._auth_data:
            self._auth_data = self._backend_service.get_s3_upload_auth_token(
                self._project.team_id, self._folder.uuid, self._project.uuid
            )
        return self._auth_data

    @property
    def s3_repo(self):

        if "error" in self.auth_data:
            raise AppException(self._auth_data.get("error"))
        return self._s3_repo(
            self.auth_data["accessKeyId"],
            self.auth_data["secretAccessKey"],
            self.auth_data["sessionToken"],
            self.auth_data["bucket"],
        )

    def validate_limitations(self):
        response = self._backend_service.get_limitations(
            team_id=self._project.team_id,
            project_id=self._project.uuid,
            folder_id=self._folder.uuid,
        )
        if not response.ok:
            raise AppValidationException(response.error)
        to_upload_count = len(self._image_urls)
        if to_upload_count > response.data.folder_limit.remaining_image_count:
            raise AppValidationException(constances.UPLOAD_FOLDER_LIMIT_ERROR_MESSAGE)
        elif to_upload_count > response.data.project_limit.remaining_image_count:
            raise AppValidationException(constances.UPLOAD_PROJECT_LIMIT_ERROR_MESSAGE)
        elif (
            response.data.user_limit
            and to_upload_count > response.data.user_limit.remaining_image_count
        ):
            raise AppValidationException(constances.UPLOAD_USER_LIMIT_ERROR_MESSAGE)

    def validate_image_names(self):
        if self._image_names and len(self._image_names) != len(self._image_urls):
            raise AppException("Not all image URLs have corresponding names.")

    def validate_project_type(self):
        if self._project.project_type in (
            constances.ProjectType.VIDEO.value,
            constances.ProjectType.DOCUMENT.value,
        ):
            raise AppValidationException(
                "The function does not support projects containing "
                f"{constances.ProjectType.get_name(self._project.project_type)} attached with URLs"
            )

    def validate_annotation_status(self):
        if self._annotation_status:
            if (
                self._annotation_status.lower()
                not in constances.AnnotationStatus.values()
            ):
                raise AppValidationException("Invalid annotations status.")
        else:
            self._annotation_status = constances.AnnotationStatus.NOT_STARTED

    def upload_image(self, image_url, image_name=None):
        download_response = DownloadImageFromPublicUrlUseCase(
            project=self._project, image_url=image_url, image_name=image_name
        ).execute()
        if not download_response.errors:
            content, content_name = download_response.data
            image_name = image_name if image_name else content_name
            duplicated_images = [
                image.name
                for image in GetBulkImages(
                    service=self._backend_service,
                    project_id=self._project.uuid,
                    team_id=self._project.team_id,
                    folder_id=self._folder.uuid,
                    images=[image_name],
                )
                .execute()
                .data
            ]
            if image_name not in duplicated_images:
                upload_response = UploadImageS3UseCase(
                    project=self._project,
                    project_settings=self._settings,
                    image_path=image_name,
                    image=content,
                    s3_repo=self.s3_repo,
                    upload_path=self.auth_data["filePath"],
                    image_quality_in_editor=self._image_quality_in_editor,
                ).execute()

                if upload_response.errors:
                    logger.warning(upload_response.errors)
                else:
                    return self.ProcessedImage(
                        url=image_url,
                        uploaded=True,
                        path=image_url,
                        entity=upload_response.data,
                    )
        logger.warning(download_response.errors)
        return self.ProcessedImage(
            url=image_url, uploaded=False, path=image_name, entity=None
        )

    def execute(self):
        if self.is_valid():
            images_to_upload = []

            logger.info("Downloading %s images", len(self._image_urls))
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=self.MAX_WORKERS
            ) as executor:
                failed_images = []
                if self._image_names:
                    results = [
                        executor.submit(self.upload_image, url, self._image_names[idx])
                        for idx, url in enumerate(self._image_urls)
                    ]
                else:
                    results = [
                        executor.submit(self.upload_image, url)
                        for url in self._image_urls
                    ]
                for future in concurrent.futures.as_completed(results):
                    processed_image = future.result()
                    if processed_image.uploaded and processed_image.entity:
                        images_to_upload.append(processed_image)
                    else:
                        failed_images.append(processed_image)
                    yield

            uploaded = []
            duplicates = []
            for i in range(0, len(images_to_upload), 100):
                response = AttachFileUrlsUseCase(
                    project=self._project,
                    folder=self._folder,
                    backend_service_provider=self._backend_service,
                    attachments=[
                        image.entity for image in images_to_upload[i : i + 100]
                    ],
                    annotation_status=self._annotation_status,
                ).execute()
                if response.errors:
                    continue
                attachments, duplications = response.data
                uploaded.extend([attachment["name"] for attachment in attachments])
                duplicates.extend([duplication["name"] for duplication in duplications])
            uploaded_image_urls = list(
                {
                    image.entity.name
                    for image in images_to_upload
                    if image.entity.name in uploaded
                }
            )
            failed_image_urls = [image.url for image in failed_images]
            self._response.data = (
                uploaded_image_urls,
                uploaded,
                duplicates,
                failed_image_urls,
            )
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
        image_quality_in_editor: str = None,
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


class InteractiveAttachFileUrlsUseCase(BaseInteractiveUseCase):
    CHUNK_SIZE = 500

    def __init__(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        attachments: List[ImageEntity],
        backend_service_provider: SuerannotateServiceProvider,
        annotation_status: str = None,
        upload_state_code: int = constances.UploadState.EXTERNAL.value,
    ):
        super().__init__()
        self._attachments = attachments
        self._project = project
        self._folder = folder
        self._backend_service = backend_service_provider
        self._annotation_status = annotation_status
        self._upload_state_code = upload_state_code

    @property
    def attachments_count(self):
        return len(self._attachments)

    @property
    def chunks_count(self):
        return int(self.attachments_count / self.CHUNK_SIZE)

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
        if (
            self._upload_state_code
            and self._upload_state_code != self._project.upload_state
        ) or self._project.upload_state == constances.UploadState.BASIC.value:
            raise AppValidationException(constances.ATTACHING_UPLOAD_STATE_ERROR)

    @property
    def annotation_status_code(self):
        if self._annotation_status:
            return constances.AnnotationStatus.get_value(self._annotation_status)
        return constances.AnnotationStatus.NOT_STARTED.value

    @property
    def upload_state_code(self) -> int:
        if not self._upload_state_code:
            return constances.UploadState.EXTERNAL.value
        return self._upload_state_code

    def execute(self):
        if self.is_valid():
            uploaded_files, duplicated_files = [], []
            for i in range(0, self.attachments_count, self.CHUNK_SIZE):
                response = AttachFileUrlsUseCase(
                    project=self._project,
                    folder=self._folder,
                    attachments=self._attachments[
                        i : i + self.CHUNK_SIZE
                    ],  # noqa: E203
                    backend_service_provider=self._backend_service,
                    annotation_status=self._annotation_status,
                    upload_state_code=self._upload_state_code,
                ).execute()
                if response.errors:
                    self._response.errors = response.errors
                    continue
                uploaded, duplicated = response.data
                uploaded_files.extend(uploaded)
                duplicated_files.extend(duplicated)
                yield len(uploaded) + len(duplicated)
            self._response.data = uploaded_files, duplicated_files
        return self._response


class CopyImageUseCase(BaseUseCase):
    def __init__(
        self,
        from_project: ProjectEntity,
        from_folder: FolderEntity,
        image_name: str,
        to_project: ProjectEntity,
        to_folder: FolderEntity,
        backend_service: SuerannotateServiceProvider,
        images: BaseManageableRepository,
        s3_repo,
        project_settings: List[ProjectSettingEntity],
        include_annotations: Optional[bool] = True,
        copy_annotation_status: Optional[bool] = True,
        copy_pin: Optional[bool] = True,
        move=False,
    ):
        super().__init__()
        self._from_project = from_project
        self._from_folder = from_folder
        self._image_name = image_name
        self._to_project = to_project
        self._to_folder = to_folder
        self._s3_repo = s3_repo
        self._project_settings = project_settings
        self._include_annotations = include_annotations
        self._copy_annotation_status = copy_annotation_status
        self._copy_pin = copy_pin
        self._backend_service = backend_service
        self._images = images
        self._move = move

    def validate_copy_path(self):
        if (
            self._from_project.name == self._to_project.name
            and self._from_folder.name == self._to_folder.name
        ):
            raise AppValidationException(
                "Cannot move image if source_project == destination_project."
            )

    def validate_project_type(self):
        if self._from_project.project_type in (
            constances.ProjectType.VIDEO.value,
            constances.ProjectType.DOCUMENT.value,
        ):
            raise AppValidationException(
                constances.LIMITED_FUNCTIONS[self._from_project.project_type]
            )

    def validate_limitations(self):
        response = self._backend_service.get_limitations(
            team_id=self._to_project.team_id,
            project_id=self._to_project.uuid,
            folder_id=self._to_folder.uuid,
        )
        if not response.ok:
            raise AppValidationException(response.error)

        if self._move and self._from_project.uuid == self._to_project.uuid:
            if self._from_folder.uuid == self._to_folder.uuid:
                raise AppValidationException(
                    "Cannot move image if source_project == destination_project."
                )

        if response.data.folder_limit.remaining_image_count < 1:
            raise AppValidationException(constances.COPY_FOLDER_LIMIT_ERROR_MESSAGE)
        if response.data.project_limit.remaining_image_count < 1:
            raise AppValidationException(constances.COPY_PROJECT_LIMIT_ERROR_MESSAGE)
        if (
            response.data.user_limit
            and response.data.user_limit.remaining_image_count < 1
        ):
            raise AppValidationException(constances.COPY_SUPER_LIMIT_ERROR_MESSAGE)

    @property
    def s3_repo(self):
        self._auth_data = self._backend_service.get_s3_upload_auth_token(
            self._to_project.team_id, self._to_folder.uuid, self._to_project.uuid
        )
        if "error" in self._auth_data:
            raise AppException(self._auth_data.get("error"))
        return self._s3_repo(
            self._auth_data["accessKeyId"],
            self._auth_data["secretAccessKey"],
            self._auth_data["sessionToken"],
            self._auth_data["bucket"],
        )

    def execute(self) -> Response:
        if self.is_valid():
            image = (
                GetImageUseCase(
                    project=self._from_project,
                    folder=self._from_folder,
                    image_name=self._image_name,
                    images=self._images,
                    service=self._backend_service,
                )
                .execute()
                .data
            )

            image_bytes = (
                GetImageBytesUseCase(
                    image=image, backend_service_provider=self._backend_service,
                )
                .execute()
                .data
            )
            image_path = f"{self._to_folder}/{self._image_name}"

            auth_data = self._backend_service.get_s3_upload_auth_token(
                team_id=self._to_project.team_id,
                folder_id=self._to_folder.uuid,
                project_id=self._to_project.uuid,
            )
            if "error" in auth_data:
                raise AppException(auth_data["error"])
            s3_response = UploadImageS3UseCase(
                project=self._to_project,
                image_path=image_path,
                image=image_bytes,
                project_settings=self._project_settings,
                upload_path=auth_data["filePath"],
                s3_repo=self.s3_repo,
            ).execute()
            if s3_response.errors:
                raise AppException(s3_response.errors)
            image_entity = s3_response.data
            del image_bytes

            attach_response = AttachFileUrlsUseCase(
                project=self._to_project,
                folder=self._to_folder,
                attachments=[image_entity],
                backend_service_provider=self._backend_service,
                annotation_status=image.annotation_status_code
                if self._copy_annotation_status
                else None,
                upload_state_code=constances.UploadState.BASIC.value,
            ).execute()
            if attach_response.errors:
                raise AppException(attach_response.errors)
            self._response.data = image_entity
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
                        idx : idx + self.CHUNK_SIZE  # noqa: E203
                    ],
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
        annotation_path: str = True,
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
        self._annotation_path = annotation_path

    def validate_project_type(self):
        if self._project.project_type in constances.LIMITED_FUNCTIONS:
            raise AppValidationException(
                constances.LIMITED_FUNCTIONS[self._project.project_type]
            )

    def execute(self):
        if self.is_valid():
            image_data = self._backend_service.get_bulk_images(
                images=[self._image_name],
                folder_id=self._folder.uuid,
                team_id=self._project.team_id,
                project_id=self._project.uuid,
            )
            if not image_data:
                raise AppException("There is no images to attach annotation.")
            image_data = image_data[0]
            response = self._backend_service.get_annotation_upload_data(
                project_id=self._project.uuid,
                team_id=self._project.team_id,
                folder_id=self._folder.uuid,
                image_ids=[image_data["id"]],
            )
            if response.ok:
                session = boto3.Session(
                    aws_access_key_id=response.data.access_key,
                    aws_secret_access_key=response.data.secret_key,
                    aws_session_token=response.data.session_token,
                    region_name=response.data.region,
                )
                resource = session.resource("s3")
                bucket = resource.Bucket(response.data.bucket)
                fill_annotation_ids(
                    annotations=self._annotations,
                    annotation_classes_name_maps=map_annotation_classes_name(self._annotation_classes.get_all()),
                    templates=self._backend_service.get_templates(self._project.team_id).get("data", []),
                    logger=logger
                )
                bucket.put_object(
                    Key=response.data.images[image_data["id"]]["annotation_json_path"],
                    Body=json.dumps(self._annotations),
                )
                if self._project.project_type == constances.ProjectType.PIXEL.value:
                    mask_path = None
                    png_path = self._annotation_path.replace(
                        "___pixel.json", "___save.png"
                    )
                    if os.path.exists(png_path) and not self._mask:
                        mask_path = png_path
                    elif self._mask:
                        mask_path = self._mask

                    if mask_path:
                        with open(mask_path, "rb") as descriptor:
                            bucket.put_object(
                                Key=response.data.images[image_data["id"]][
                                    "annotation_bluemap_path"
                                ],
                                Body=descriptor.read(),
                            )
                if self._verbose:
                    logger.info(
                        "Uploading annotations for image %s in project %s.",
                        str(image_data["name"]),
                        self._project.name,
                    )
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
        if self._project.project_type in constances.LIMITED_FUNCTIONS:
            raise AppValidationException(
                constances.LIMITED_FUNCTIONS[self._project.project_type]
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


class UploadAnnotationsUseCase(BaseInteractiveUseCase):
    MAX_WORKERS = 10
    CHUNK_SIZE = 100
    AUTH_DATA_CHUNK_SIZE = 500

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
        self._annotations_to_upload = None
        self._missing_annotations = None
        self.missing_attribute_groups = set()
        self.missing_classes = set()
        self.missing_attributes = set()

    @property
    def s3_client(self):
        return boto3.client("s3")

    @property
    def annotation_postfix(self):
        return (
            constances.VECTOR_ANNOTATION_POSTFIX
            if self._project.project_type == constances.ProjectType.VECTOR.value
            else constances.PIXEL_ANNOTATION_POSTFIX
        )

    @property
    def annotations_to_upload(self):
        if not self._annotations_to_upload:
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
            if not annotations_to_upload:
                raise AppException("No image to attach annotations.")
            self._missing_annotations = missing_annotations
            self._annotations_to_upload = annotations_to_upload
        return self._annotations_to_upload

    def _is_valid_json(self, json_data: dict):
        try:
            if self._project.project_type == constances.ProjectType.PIXEL.value:
                PixelAnnotation(**json_data)
            else:
                VectorAnnotation(**json_data)
            return True
        except ValidationError as _:
            return False

    def execute(self):
        uploaded_annotations = []
        missing_annotations = []
        failed_annotations = []
        for _ in range(0, len(self.annotations_to_upload), self.AUTH_DATA_CHUNK_SIZE):
            annotations_to_upload = self.annotations_to_upload[
                _ : _ + self.AUTH_DATA_CHUNK_SIZE  # noqa: E203
            ]

            if self._pre_annotation:
                response = self._backend_service.get_pre_annotation_upload_data(
                    project_id=self._project.uuid,
                    team_id=self._project.team_id,
                    folder_id=self._folder.uuid,
                    image_ids=[int(image.id) for image in annotations_to_upload],
                )
            else:
                response = self._backend_service.get_annotation_upload_data(
                    project_id=self._project.uuid,
                    team_id=self._project.team_id,
                    folder_id=self._folder.uuid,
                    image_ids=[int(image.id) for image in annotations_to_upload],
                )
            if response.ok:
                session = boto3.Session(
                    aws_access_key_id=response.data.access_key,
                    aws_secret_access_key=response.data.secret_key,
                    aws_session_token=response.data.session_token,
                    region_name=response.data.region,
                )
                resource = session.resource("s3")
                bucket = resource.Bucket(response.data.bucket)
                image_id_name_map = {
                    image.id: image for image in self.annotations_to_upload
                }
                if self._client_s3_bucket:
                    from_session = boto3.Session()
                    from_s3 = from_session.resource("s3")
                else:
                    from_s3 = None

                for _ in range(len(annotations_to_upload) - len(response.data.images)):
                    yield
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=self.MAX_WORKERS
                ) as executor:
                    results = [
                        executor.submit(
                            self.upload_to_s3,
                            image_id,
                            image_info,
                            bucket,
                            from_s3,
                            image_id_name_map,
                        )
                        for image_id, image_info in response.data.images.items()
                    ]
                    for future in concurrent.futures.as_completed(results):
                        annotation, uploaded = future.result()
                        if uploaded:
                            uploaded_annotations.append(annotation)
                        else:
                            failed_annotations.append(annotation)
                        yield

        uploaded_annotations = [annotation.path for annotation in uploaded_annotations]
        missing_annotations.extend(
            [annotation.path for annotation in self._missing_annotations]
        )
        failed_annotations = [annotation.path for annotation in failed_annotations]
        self._response.data = (
            uploaded_annotations,
            failed_annotations,
            missing_annotations,
        )
        self.report_missing_data()
        return self._response

    def upload_to_s3(
        self, image_id: int, image_info, bucket, from_s3, image_id_name_map
    ):
        try:
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
            report = fill_annotation_ids(
                annotations=annotation_json,
                annotation_classes_name_maps=map_annotation_classes_name(self._annotation_classes),
                templates=self._templates
            )
            self.missing_classes.update(report["missing_classes"])
            self.missing_attribute_groups.update(report["missing_attribute_groups"])
            self.missing_attributes.update(report["missing_attributes"])
            if not self._is_valid_json(annotation_json):
                logger.warning(f"Invalid json {image_id_name_map[image_id].path}")
                return image_id_name_map[image_id], False
            bucket.put_object(
                Key=image_info["annotation_json_path"],
                Body=json.dumps(annotation_json),
            )
            if self._project.project_type == constances.ProjectType.PIXEL.value:
                mask_path = image_id_name_map[image_id].path.replace(
                    "___pixel.json", constances.ANNOTATION_MASK_POSTFIX
                )
                if from_s3:
                    file = io.BytesIO()
                    s3_object = from_s3.Object(self._client_s3_bucket, mask_path)
                    s3_object.download_fileobj(file)
                    file.seek(0)
                else:
                    with open(mask_path, "rb") as mask_file:
                        file = io.BytesIO(mask_file.read())
                bucket.put_object(Key=image_info["annotation_bluemap_path"], Body=file)
            return image_id_name_map[image_id], True
        except Exception as e:
            self._response.report = f"Couldn't upload annotation {image_id_name_map[image_id].name} - {str(e)}"
            return image_id_name_map[image_id], False

    def report_missing_data(self):
        if self.missing_classes:
            logger.warning(f"Couldn't find classes [{', '.join(self.missing_classes)}]")
        if self.missing_attribute_groups:
            logger.warning(
                f"Couldn't find annotation groups [{', '.join(self.missing_attribute_groups)}]"
            )
        if self.missing_attributes:
            logger.warning(
                f"Couldn't find attributes [{', '.join(self.missing_attributes)}]"
            )


class DownloadImageAnnotationsUseCase(BaseUseCase):
    def __init__(
        self,
        service: SuerannotateServiceProvider,
        project: ProjectEntity,
        folder: FolderEntity,
        image_name: str,
        images: BaseManageableRepository,
        destination: str,
        annotation_classes: BaseManageableRepository,
    ):
        super().__init__()
        self._service = service
        self._project = project
        self._folder = folder
        self._image_name = image_name
        self._images = images
        self._destination = destination
        self._annotation_classes = annotation_classes

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
        if self._project.project_type in constances.LIMITED_FUNCTIONS:
            raise AppValidationException(
                constances.LIMITED_FUNCTIONS[self._project.project_type]
            )

    @property
    def annotation_classes_id_name_map(self) -> dict:
        classes_data = defaultdict(dict)
        annotation_classes = self._annotation_classes.get_all()
        for annotation_class in annotation_classes:
            class_info = {"name": annotation_class.name, "attribute_groups": {}}
            if annotation_class.attribute_groups:
                for attribute_group in annotation_class.attribute_groups:
                    attribute_group_data = defaultdict(dict)
                    for attribute in attribute_group["attributes"]:
                        attribute_group_data[attribute["id"]] = attribute["name"]
                    class_info["attribute_groups"] = {
                        attribute_group["id"]: {
                            "name": attribute_group["name"],
                            "attributes": attribute_group_data,
                        }
                    }
            classes_data[annotation_class.uuid] = class_info
        return classes_data

    def get_templates_mapping(self):
        templates = self._service.get_templates(team_id=self._project.team_id).get(
            "data", []
        )
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
                for i in annotation["attributes"]
                if "groupId" in i
                and i["groupId"] in annotation_class["attribute_groups"].keys()
            ]:
                attribute["groupName"] = annotation_class["attribute_groups"][
                    attribute["groupId"]
                ]["name"]
                if attribute["id"] not in list(
                    annotation_class["attribute_groups"][attribute["groupId"]][
                        "attributes"
                    ].keys()
                ):
                    continue
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
        if self._project.project_type in constances.LIMITED_FUNCTIONS:
            raise AppValidationException(
                constances.LIMITED_FUNCTIONS[self._project.project_type]
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
        if self._project.project_type in constances.LIMITED_FUNCTIONS:
            raise AppValidationException(
                constances.LIMITED_FUNCTIONS[self._project.project_type]
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
        if self._project.project_type in constances.LIMITED_FUNCTIONS:
            raise AppValidationException(
                constances.LIMITED_FUNCTIONS[self._project.project_type]
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
                    f"Cant un assign {', '.join(self._image_names[i: i + self.CHUNK_SIZE])}"
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
        if project.project_type in constances.LIMITED_FUNCTIONS:
            raise AppValidationException(
                constances.LIMITED_FUNCTIONS[project.project_type]
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
                        i : i + self.CHUNK_SIZE  # noqa: E203
                    ],
                    team_id=self._team_id,
                    project_id=self._project_id,
                    folder_id=self._folder_id,
                    annotation_status=self._annotation_status,
                )
                if not status_changed:
                    self._response.errors = AppException("Failed to change status.")
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
        json_path = f"{self._download_path}/classes.json"
        json.dump(classes, open(json_path, "w"), indent=4)
        self._response.data = json_path
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

    def validate_annotation_classes(self):
        if "attribute_groups" not in self._annotation_classes:
            raise AppValidationException("Field attribute_groups is required.")

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


class UploadFileToS3UseCase(BaseUseCase):
    def __init__(self, to_s3_bucket, path, s3_key: str):
        super().__init__()
        self._to_s3_bucket = to_s3_bucket
        self._path = path
        self._s3_key = s3_key

    def execute(self):
        self._to_s3_bucket.upload_file(str(self._path), self._s3_key)


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
        self._limitation_response = None

    def validate_upload_state(self):
        if self._project.upload_state == constances.UploadState.EXTERNAL.value:
            raise AppValidationException(constances.UPLOADING_UPLOAD_STATE_ERROR)

    @property
    def limitation_response(self):
        if not self._limitation_response:
            self._limitation_response = self._backend_service.get_limitations(
                team_id=self._project.team_id,
                project_id=self._project.uuid,
                folder_id=self._folder.uuid,
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
            self._limitation_response.data.folder_limit.remaining_image_count,
            self._limitation_response.data.project_limit.remaining_image_count,
        ]
        if self._limitation_response.data.user_limit:
            limits.append(
                self._limitation_response.data.user_limit.remaining_image_count
            )
        return min(limits)

    def validate_project_type(self):
        if self._project.project_type in constances.LIMITED_FUNCTIONS:
            raise AppValidationException(
                constances.LIMITED_FUNCTIONS[self._project.project_type]
            )

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
