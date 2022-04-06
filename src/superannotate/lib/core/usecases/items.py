import copy
from typing import List

import superannotate.lib.core as constances
from lib.core.conditions import Condition
from lib.core.conditions import CONDITION_EQ as EQ
from lib.core.entities import DocumentEntity
from lib.core.entities import Entity
from lib.core.entities import FolderEntity
from lib.core.entities import ProjectEntity
from lib.core.entities import TmpBaseEntity
from lib.core.entities import TmpImageEntity
from lib.core.entities import VideoEntity
from lib.core.exceptions import AppException
from lib.core.reporter import Reporter
from lib.core.repositories import BaseReadOnlyRepository
from lib.core.response import Response
from lib.core.serviceproviders import SuperannotateServiceProvider
from lib.core.usecases.base import BaseReportableUseCae
from pydantic import parse_obj_as


class GetItem(BaseReportableUseCae):
    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        folder: FolderEntity,
        items: BaseReadOnlyRepository,
        item_name: str,
    ):
        super().__init__(reporter)
        self._project = project
        self._folder = folder
        self._items = items
        self._item_name = item_name

    @staticmethod
    def serialize_entity(entity: Entity, project: ProjectEntity):
        if project.upload_state != constances.UploadState.EXTERNAL.value:
            entity.url = None
        if project.project_type in (
            constances.ProjectType.VECTOR.value,
            constances.ProjectType.PIXEL.value,
        ):
            tmp_entity = entity
            if project.project_type == constances.ProjectType.VECTOR.value:
                entity.segmentation_status = None
            if project.upload_state == constances.UploadState.EXTERNAL.value:
                tmp_entity.prediction_status = None
                tmp_entity.segmentation_status = None
            return TmpImageEntity(**tmp_entity.dict(by_alias=True))
        elif project.project_type == constances.ProjectType.VIDEO.value:
            return VideoEntity(**entity.dict(by_alias=True))
        elif project.project_type == constances.ProjectType.DOCUMENT.value:
            return DocumentEntity(**entity.dict(by_alias=True))
        return entity

    def execute(self) -> Response:
        if self.is_valid():
            condition = (
                Condition("name", self._item_name, EQ)
                & Condition("team_id", self._project.team_id, EQ)
                & Condition("project_id", self._project.uuid, EQ)
                & Condition("folder_id", self._folder.uuid, EQ)
            )
            entity = self._items.get_one(condition)
            if entity:
                entity.add_path(self._project.name, self._folder.name)
                self._response.data = self.serialize_entity(entity, self._project)
            else:
                self._response.errors = AppException("Item not found.")
        return self._response


class QueryEntities(BaseReportableUseCae):
    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        folder: FolderEntity,
        backend_service_provider: SuperannotateServiceProvider,
        query: str,
    ):
        super().__init__(reporter)
        self._project = project
        self._folder = folder
        self._backend_client = backend_service_provider
        self._query = query

    def validate_query(self):
        response = self._backend_client.validate_saqul_query(
            self._project.team_id, self._project.uuid, self._query
        )
        if response.get("error"):
            raise AppException(response["error"])
        if response["isValidQuery"]:
            self._query = response["parsedQuery"]
        else:
            raise AppException("Incorrect query.")
        if self._project.sync_status != constances.ProjectState.SYNCED.value:
            raise AppException("Data is not synced.")

    def execute(self) -> Response:
        if self.is_valid():
            service_response = self._backend_client.saqul_query(
                self._project.team_id,
                self._project.uuid,
                self._query,
                folder_id=None if self._folder.name == "root" else self._folder.uuid,
            )
            if service_response.ok:
                data = parse_obj_as(List[TmpBaseEntity], [Entity.map_fields(i) for i in service_response.data])
                for i, item in enumerate(data):
                    data[i] = GetItem.serialize_entity(item, self._project)
                self._response.data = data
            else:
                self._response.errors = service_response.data
        return self._response


class ListItems(BaseReportableUseCae):
    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        folder: FolderEntity,
        items: BaseReadOnlyRepository,
        search_condition: Condition,
        folders: BaseReadOnlyRepository,
        recursive: bool = False,
    ):
        super().__init__(reporter)
        self._project = project
        self._folder = folder
        self._items = items
        self._folders = folders
        self._search_condition = search_condition
        self._recursive = recursive

    def validate_recursive_case(self):
        if not self._folder.is_root and self._recursive:
            self._recursive = False

    def execute(self) -> Response:
        if self.is_valid():
            self._search_condition &= Condition("team_id", self._project.team_id, EQ)
            self._search_condition &= Condition("project_id", self._project.uuid, EQ)

            if not self._recursive:
                self._search_condition &= Condition("folder_id", self._folder.uuid, EQ)
                items = [
                    GetItem.serialize_entity(
                        item.add_path(self._project.name, self._folder.name),
                        self._project,
                    )
                    for item in self._items.get_all(self._search_condition)
                ]
            else:
                items = []
                folders = self._folders.get_all(
                    Condition("team_id", self._project.team_id, EQ)
                    & Condition("project_id", self._project.uuid, EQ),
                )
                folders.append(self._folder)
                for folder in folders:
                    tmp = self._items.get_all(
                        copy.deepcopy(self._search_condition) & Condition("folder_id", folder.uuid, EQ)
                    )
                    items.extend(
                        [
                            GetItem.serialize_entity(
                                item.add_path(self._project.name, folder.name),
                                self._project,
                            )
                            for item in tmp
                        ]
                    )
            self._response.data = items
        return self._response
