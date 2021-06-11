import io
import uuid
from abc import ABC
from abc import abstractmethod
from pathlib import Path
from typing import List
from typing import Optional

import src.lib.core as constances
from src.lib.core.conditions import Condition
from src.lib.core.conditions import CONDITION_EQ as EQ
from src.lib.core.entities import ImageFileEntity
from src.lib.core.entities import ImageInfoEntity
from src.lib.core.entities import ProjectEntity
from src.lib.core.exceptions import AppException
from src.lib.core.exceptions import AppValidationException
from src.lib.core.plugin import ImagePlugin
from src.lib.core.repositories import BaseManageableRepository
from src.lib.core.repositories import BaseReadOnlyRepository
from src.lib.core.response import Response
from src.lib.core.serviceproviders import SuerannotateServiceProvider


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
        projects: BaseManageableRepository,
    ):
        super().__init__(response)
        self._condition = condition
        self._projects = projects

    def execute(self):
        if self.is_valid():
            self._response.data = self._projects.get_all(self._condition)
        self._response.errors = self._errors


class CreateProjectUseCase(BaseUseCase):
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
            self._projects.insert(self._project)
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
        upload_path: str,
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
        self._upload_path = upload_path

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

        self._backend.create_image(
            project_id=self._project.uuid,
            team_id=self._project.team_id,
            images=images,
            annotation_status_code=self.annotation_status_code,
            upload_state_code=self.upload_state_code,
            meta=meta,
            annotation_json_path=self._upload_path + ".json",
            annotation_bluemap_path=self._upload_path + ".png",
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
        if self._project.project_type == "Vector":
            return constances.MAX_VECTOR_RESOLUTION
        elif self._project.project_type == "Pixel":
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
            path=self._upload_path + image_key,
            width=origin_width,
            height=origin_height,
        )
