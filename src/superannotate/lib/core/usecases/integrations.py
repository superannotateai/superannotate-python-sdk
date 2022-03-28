from typing import List

from lib.core.entities import FolderEntity
from lib.core.entities import IntegrationEntity
from lib.core.entities import ProjectEntity
from lib.core.entities import TeamEntity
from lib.core.exceptions import AppException
from lib.core.reporter import Reporter
from lib.core.repositories import BaseReadOnlyRepository
from lib.core.response import Response
from lib.core.serviceproviders import SuperannotateServiceProvider
from lib.core.usecases import BaseReportableUseCae


class GetIntegrations(BaseReportableUseCae):
    def __init__(
        self,
        reporter: Reporter,
        team: TeamEntity,
        integrations: BaseReadOnlyRepository,
    ):

        super().__init__(reporter)
        self._team = team
        self._integrations = integrations

    def execute(self) -> Response:
        integrations = self._integrations.get_all()
        integrations = list(sorted(integrations, key=lambda x: x.createdAt))
        integrations.reverse()
        self._response.data = integrations
        return self._response


class AttachIntegrations(BaseReportableUseCae):
    def __init__(
        self,
        reporter: Reporter,
        team: TeamEntity,
        project: ProjectEntity,
        folder: FolderEntity,
        integrations: BaseReadOnlyRepository,
        backend_service: SuperannotateServiceProvider,
        integration: IntegrationEntity,
        folder_path: str = None,
    ):

        super().__init__(reporter)
        self._project = project
        self._folder = folder
        self._team = team
        self._integration = integration
        self._client = backend_service
        self._folder_path = folder_path
        self._integrations = integrations

    @property
    def _upload_path(self):
        return f"{self._project.name}{f'/{self._folder.name}' if self._folder.name != 'root' else ''}"

    def execute(self) -> Response:
        integrations: List[IntegrationEntity] = self._integrations.get_all()
        integration_name_lower = self._integration.name.lower()
        integration = next(
            (i for i in integrations if i.name.lower() == integration_name_lower), None
        )
        if integration:
            self.reporter.log_info(
                "Attaching file(s) from "
                f"{integration.root}{f'/{self._folder_path}' if self._folder_path else ''} "
                f"to {self._upload_path}. This may take some time."
            )
            attached = self._client.attach_integrations(
                self._team.uuid,
                self._project.uuid,
                integration.id,
                self._folder.uuid,
                self._folder_path,
            )
            if not attached:
                self._response.errors = AppException(
                    f"An error occurred for {self._integration.name}. Please make sure: "
                    "\n - The bucket exists."
                    "\n - The connection is valid."
                    "\n - The path to a specified directory is correct."
                )
        else:
            self._response.errors = AppException("Integration not found.")
        return self._response
