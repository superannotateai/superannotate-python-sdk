from typing import List

from lib.core.entities import ProjectEntity
from lib.core.reporter import Reporter
from lib.core.response import Response
from lib.core.serviceproviders import SuperannotateServiceProvider
from lib.core.usecases import BaseReportableUseCase


class CreateCustomSchemaUseCase(BaseReportableUseCase):
    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        schema: dict,
        backend_client: SuperannotateServiceProvider,
    ):
        super().__init__(reporter)
        self._project = project
        self._schema = schema
        self._backend_client = backend_client

    def execute(self) -> Response:
        response = self._backend_client.create_custom_schema(
            team_id=self._project.team_id,
            project_id=self._project.id,
            schema=self._schema,
        )
        if response.ok:
            self._response.data = response.data
        else:
            self._response.errors = response.error
        return self._response


class GetCustomSchemaUseCase(BaseReportableUseCase):
    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        backend_client: SuperannotateServiceProvider,
    ):
        super().__init__(reporter)
        self._project = project
        self._backend_client = backend_client

    def execute(self) -> Response:
        response = self._backend_client.get_custom_schema(
            team_id=self._project.team_id,
            project_id=self._project.id,
        )
        if response.ok:
            self._response.data = response.data
        else:
            self._response.errors = response.error
        return self._response


class DeleteCustomSchemaUseCase(BaseReportableUseCase):
    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        fields: List[str],
        backend_client: SuperannotateServiceProvider,
    ):
        super().__init__(reporter)
        self._project = project
        self._fields = fields
        self._backend_client = backend_client

    def execute(self) -> Response:
        response = self._backend_client.delete_custom_schema(
            team_id=self._project.team_id,
            project_id=self._project.id,
            fields=self._fields,
        )
        if response.ok:
            self._response.data = response.data
        else:
            self._response.errors = response.error
        return self._response
