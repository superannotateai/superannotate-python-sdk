from typing import List

import superannotate.lib.core as constances
from lib.core.entities.project_entities import Entity
from lib.core.entities.project_entities import FolderEntity
from lib.core.entities.project_entities import ProjectEntity
from lib.core.entities.project_entities import TmpImageEntity
from lib.core.exceptions import AppException
from lib.core.reporter import Reporter
from lib.core.response import Response
from lib.core.serviceproviders import SuperannotateServiceProvider
from lib.core.usecases.base import BaseReportableUseCae
from pydantic import parse_obj_as


class QueryEntities(BaseReportableUseCae):
    def __init__(
            self,
            reporter: Reporter,
            project: ProjectEntity,
            folder: FolderEntity,
            backend_service_provider: SuperannotateServiceProvider,
            query: str

    ):
        super().__init__(reporter)
        self._project = project
        self._folder = folder
        self._backend_client = backend_service_provider
        self._query = query

    def validate_query(self):
        response = self._backend_client.validate_saqul_query(self._project.team_id, self._project.uuid, self._query)
        if response.get("error"):
            raise AppException(response["error"])
        if not response.get("isValidQuery", False):
            raise AppException("Incorrect query.")

    def execute(self) -> Response:
        if self.is_valid():
            service_response = self._backend_client.saqul_query(
                self._project.team_id,
                self._project.uuid,
                self._folder.uuid,
                self._query
            )
            if service_response.ok:
                if self._project.project_type == constances.ProjectType.VECTOR.value:
                    self._response.data = parse_obj_as(List[TmpImageEntity], service_response.data)
                else:
                    self._response.data = parse_obj_as(List[Entity], service_response.data)
            else:
                self._response.errors = service_response.data
        return self._response
