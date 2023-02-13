import json
import logging
from typing import List

from lib.core.conditions import Condition
from lib.core.conditions import CONDITION_EQ as EQ
from lib.core.entities import AnnotationClassEntity
from lib.core.entities import ProjectEntity
from lib.core.enums import ProjectType
from lib.core.exceptions import AppException
from lib.core.serviceproviders import BaseServiceProvider
from lib.core.usecases.base import BaseUseCase

logger = logging.getLogger("sa")


class GetAnnotationClassesUseCase(BaseUseCase):
    def __init__(
        self,
        service_provider: BaseServiceProvider,
        condition: Condition = None,
    ):
        super().__init__()
        self._service_provider = service_provider
        self._condition = condition

    def execute(self):
        response = self._service_provider.annotation_classes.list(self._condition)
        if response.ok:
            self._response.data = response.data
        else:
            self._response.errors = response.error
        return self._response


class CreateAnnotationClassUseCase(BaseUseCase):
    def __init__(
        self,
        service_provider: BaseServiceProvider,
        annotation_class: AnnotationClassEntity,
        project: ProjectEntity,
    ):
        super().__init__()
        self._service_provider = service_provider
        self._annotation_class = annotation_class
        self._project = project

    def _is_unique(self):
        annotation_classes = self._service_provider.annotation_classes.list(
            Condition("project_id", self._project.id, EQ)
        ).data
        return not any(
            [
                True
                for annotation_class in annotation_classes
                if annotation_class.name == self._annotation_class.name
            ]
        )

    def validate_project_type(self):
        if (
            self._project.type == ProjectType.PIXEL
            and self._annotation_class.type == "tag"
        ):
            raise AppException(
                "Predefined tagging functionality is not supported for projects"
                f" of type {ProjectType.get_name(self._project.type)}."
            )

    def validate_default_value(self):
        if self._project.type == ProjectType.PIXEL.value and any(
            getattr(attr_group, "default_value", None)
            for attr_group in getattr(self._annotation_class, "attribute_groups", [])
        ):
            raise AppException(
                'The "default_value" key is not supported for project type Pixel.'
            )

    def execute(self):
        if self.is_valid():
            if self._is_unique():
                response = self._service_provider.annotation_classes.create_multiple(
                    project=self._project,
                    classes=[self._annotation_class],
                )
                if response.ok:
                    self._response.data = response.data[0]
                else:
                    self._response.errors = AppException(
                        response.error.replace(". ", ".\n")
                    )
            else:
                logger.error("This class name already exists. Skipping.")
        return self._response


class CreateAnnotationClassesUseCase(BaseUseCase):
    CHUNK_SIZE = 500

    def __init__(
        self,
        service_provider: BaseServiceProvider,
        annotation_classes: List[AnnotationClassEntity],
        project: ProjectEntity,
    ):
        super().__init__()
        self._project = project
        self._service_provider = service_provider
        self._annotation_classes = annotation_classes

    def validate_project_type(self):
        if self._project.type == ProjectType.PIXEL and any(
            [True for i in self._annotation_classes if i.type == "tag"]
        ):
            raise AppException(
                f"Predefined tagging functionality is not supported"
                f" for projects of type {ProjectType.get_name(self._project.type)}."
            )

    def validate_default_value(self):
        if self._project.type == ProjectType.PIXEL.value:
            for annotation_class in self._annotation_classes:
                if any(
                    getattr(attr_group, "default_value", None)
                    for attr_group in getattr(annotation_class, "attribute_groups", [])
                ):
                    raise AppException(
                        'The "default_value" key is not supported for project type Pixel.'
                    )

    def execute(self):
        if self.is_valid():
            existing_annotation_classes = (
                self._service_provider.annotation_classes.list(
                    Condition("project_id", self._project.id, EQ)
                ).data
            )
            existing_classes_name = [i.name for i in existing_annotation_classes]
            unique_annotation_classes = []
            for annotation_class in self._annotation_classes:
                if annotation_class.name not in existing_classes_name:
                    unique_annotation_classes.append(annotation_class)
            not_unique_classes_count = len(self._annotation_classes) - len(
                unique_annotation_classes
            )
            if not_unique_classes_count:
                logger.warning(
                    f"{not_unique_classes_count} annotation classes already exist.Skipping."
                )
            created = []
            chunk_failed = False
            # this is in reverse order because of the front-end
            for i in range(len(unique_annotation_classes), 0, -self.CHUNK_SIZE):
                response = self._service_provider.annotation_classes.create_multiple(
                    project=self._project,
                    classes=unique_annotation_classes[i - self.CHUNK_SIZE : i],  # noqa
                )
                if response.ok:
                    created.extend(response.data)
                else:
                    logger.debug(response.error)
                    chunk_failed = True
            if created:
                logger.info(
                    f"{len(created)} annotation classes were successfully created in {self._project.name}."
                )
            if chunk_failed:
                self._response.errors = AppException(
                    "The classes couldn't be validated."
                )
            self._response.data = created
        return self._response


class DownloadAnnotationClassesUseCase(BaseUseCase):
    def __init__(
        self,
        download_path: str,
        project: ProjectEntity,
        service_provider: BaseServiceProvider,
    ):
        super().__init__()
        self._download_path = download_path
        self._project = project
        self._service_provider = service_provider

    def execute(self):
        logger.info(
            f"Downloading classes.json from project {self._project.name} to folder {str(self._download_path)}."
        )
        response = self._service_provider.annotation_classes.list(
            Condition("project_id", self._project.id, EQ)
        )
        if response.ok:
            classes = [
                entity.dict(by_alias=True, exclude_unset=True)
                for entity in response.data
            ]
            json_path = f"{self._download_path}/classes.json"
            json.dump(classes, open(json_path, "w"), indent=4)
            self._response.data = json_path
        return self._response
