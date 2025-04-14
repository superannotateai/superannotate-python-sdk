import json
from abc import ABC
from abc import abstractmethod
from io import StringIO
from typing import Any

from lib.core.entities import BaseItemEntity
from lib.core.entities import FolderEntity
from lib.core.entities import ProjectEntity
from lib.core.utils import run_async
from lib.infrastructure.controller import Controller


class BaseMultimodalAnnotationAdapter(ABC):
    def __init__(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        item: BaseItemEntity,
        controller: Controller,
        annotation: dict = None,
    ):
        self._project = project
        self._folder = folder
        self._item = item
        self._controller = controller
        self._annotation = annotation

    @property
    @abstractmethod
    def annotation(self) -> dict:
        raise NotImplementedError

    def get_metadata(self):
        return self.annotation["metadata"]

    @abstractmethod
    def save(self):
        raise NotImplementedError

    def get_component_value(self, component_id: str):
        component_data = self.annotation.get("data", {}).get(component_id)
        if isinstance(component_data, dict):
            return component_data.get("value")
        elif isinstance(component_data, list):
            # Find the dict with the smallest element_path
            annotation = min(
                (
                    elem
                    for elem in component_data
                    if isinstance(elem, dict) and "element_path" in elem
                ),
                key=lambda x: x["element_path"],
                default=None,
            )
            if annotation is not None:
                return annotation.get("value")
        return None

    def set_component_value(self, component_id: str, value: Any):
        data = self.annotation.setdefault("data", {})
        component_data = data.get(component_id)

        if component_data is None:
            data[component_id] = [{"value": value}]
        elif isinstance(component_data, dict):
            component_data["value"] = value
        elif isinstance(component_data, list):
            # Find the dict with the smallest element_path
            annotation = min(
                (
                    elem
                    for elem in component_data
                    if isinstance(elem, dict) and "element_path" in elem
                ),
                key=lambda x: x["element_path"],
                default=None,
            )
            if annotation is not None:
                annotation["value"] = value

        return self


class MultimodalSmallAnnotationAdapter(BaseMultimodalAnnotationAdapter):
    def __init__(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        item: BaseItemEntity,
        controller: Controller,
        overwrite: bool = True,
        annotation: dict = None,
    ):
        super().__init__(project, folder, item, controller, annotation)
        self._etag = annotation.get("metadata", {}).get("etag") if annotation else None
        self._overwrite = overwrite

    @property
    def annotation(self) -> dict:
        if self._annotation is None:
            response = self._controller.annotations.get_item_annotations(
                project=self._project,
                folder=self._folder,
                item_id=self._item.id,
                transform_version="llmJsonV3",
            )
            if not response or response.status_code == 404:
                self._annotation = {
                    "metadata": {"id": self._item.id, "name": self._item.name},
                    "data": dict(),
                }
            else:
                self._annotation = json.loads(response.data)
                self._etag = self._annotation["metadata"]["etag"]
        return self._annotation

    def save(self):
        self._controller.annotations.set_item_annotations(
            project=self._project,
            folder=self._folder,
            item_id=self._item.id,
            transform_version="llmJsonV3",
            data=self.annotation,
            overwrite=self._overwrite,
            etag=self._etag,
        )


class MultimodalLargeAnnotationAdapter(BaseMultimodalAnnotationAdapter):
    @property
    def annotation(self) -> dict:
        if self._annotation is None:
            self._annotation = run_async(
                self._controller.service_provider.annotations.get_big_annotation(
                    project=self._project,
                    item=self._item,
                    reporter=self._controller.reporter,
                    transform_version="llmJsonV3",
                )
            )
        return self._annotation

    def save(self):
        run_async(
            self._controller.service_provider.annotations.upload_big_annotation(
                project=self._project,
                folder=self._folder,
                item_id=self._item.id,
                data=StringIO(json.dumps(self._annotation)),
                chunk_size=5 * 1024 * 1024,
                transform_version="llmJsonV3",
            )
        )
