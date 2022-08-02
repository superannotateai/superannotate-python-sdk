import json
from typing import List

from lib.core.entities import AnnotationClassEntity
from lib.core.entities import ProjectEntity
from lib.core.enums import ProjectType
from lib.core.exceptions import AppException
from lib.core.reporter import Reporter
from lib.core.serviceproviders import SuperannotateServiceProvider
from lib.core.usecases.base import BaseReportableUseCase


class CreateAnnotationClassUseCase(BaseReportableUseCase):
    def __init__(
        self,
        reporter: Reporter,
        backend_client: SuperannotateServiceProvider,
        annotation_class: AnnotationClassEntity,
        project: ProjectEntity,
    ):
        super().__init__(reporter)
        self._backend_client = backend_client
        self._annotation_class = annotation_class
        self._project = project

    def _is_unique(self):
        annotation_classes = self._backend_client.list_annotation_classes(
            project_id=self._project.id, team_id=self._project.team_id
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
            self._project.type in (ProjectType.PIXEL.value, ProjectType.VIDEO.value)
            and self._annotation_class.type == "tag"
        ):
            raise AppException(
                f"Predefined tagging functionality is not supported for projects"
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
                self.reporter.log_info(
                    f"Creating annotation class in project {self._project.name} with name {self._annotation_class.name}"
                )
                response = self._backend_client.create_annotation_classes(
                    project_id=self._project.id,
                    team_id=self._project.team_id,
                    data=[self._annotation_class],
                )
                if response.ok:
                    self._response.data = response.data[0]
                else:
                    self._response.errors = response.error
            else:
                self.reporter.log_error(
                    "The annotation class is already in project. Skipping."
                )
                self._response.data = None
        return self._response


class CreateAnnotationClassesUseCase(BaseReportableUseCase):
    CHUNK_SIZE = 500

    def __init__(
        self,
        reporter: Reporter,
        backend_client: SuperannotateServiceProvider,
        annotation_classes: List[AnnotationClassEntity],
        project: ProjectEntity,
    ):
        super().__init__(reporter)
        self._project = project
        self._backend_client = backend_client
        self._annotation_classes = annotation_classes

    def validate_project_type(self):
        if self._project.type in (
            ProjectType.PIXEL.value,
            ProjectType.VIDEO.value,
        ) and any([True for i in self._annotation_classes if i.type == "tag"]):
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
            self.reporter.log_info(
                f"Creating annotation classes in project {self._project.name}."
            )
            existing_annotation_classes = self._backend_client.list_annotation_classes(
                project_id=self._project.id, team_id=self._project.team_id
            ).data
            existing_classes_name = [i.name for i in existing_annotation_classes]
            unique_annotation_classes = []
            for annotation_class in self._annotation_classes:
                if annotation_class.name in existing_classes_name:
                    self.reporter.log_error(
                        f"Annotation class {annotation_class.name} already in project. Skipping."
                    )
                    continue
                else:
                    unique_annotation_classes.append(annotation_class)
            created = []
            # this is in reverse order because of the front-end
            for i in range(len(unique_annotation_classes), 0, -self.CHUNK_SIZE):
                response = self._backend_client.create_annotation_classes(
                    project_id=self._project.id,
                    team_id=self._project.team_id,
                    data=unique_annotation_classes[i - self.CHUNK_SIZE : i],  # noqa
                )
                if response.ok:
                    created.extend(response.data)
                else:
                    if created:
                        self.reporter.log_info(
                            f"{len(created)} annotation classes were successfully created in {self._project.name}."
                        )
                    self._response.errors = AppException(
                        "Couldn't validate annotation classes."
                    )
                    break
            self._response.data = created
        return self._response


class DownloadAnnotationClassesUseCase(BaseReportableUseCase):
    def __init__(
        self,
        reporter: Reporter,
        download_path: str,
        project: ProjectEntity,
        backend_client: SuperannotateServiceProvider,
    ):
        super().__init__(reporter)
        self._download_path = download_path
        self._project = project
        self._backend_client = backend_client

    def execute(self):
        self.reporter.log_info(
            f"Downloading classes.json from project {self._project.name} to folder {str(self._download_path)}."
        )
        response = self._backend_client.list_annotation_classes(
            project_id=self._project.id, team_id=self._project.team_id
        )
        if response.ok:
            classes = [
                entity.dict(by_alias=True, fill_enum_values=True)
                for entity in response.data
            ]
            json_path = f"{self._download_path}/classes.json"
            json.dump(classes, open(json_path, "w"), indent=4)
            self._response.data = json_path
        return self._response
