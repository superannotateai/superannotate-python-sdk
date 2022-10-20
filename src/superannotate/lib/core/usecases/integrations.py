from typing import List

from lib.core.entities import FolderEntity
from lib.core.entities import IntegrationEntity
from lib.core.entities import ProjectEntity
from lib.core.exceptions import AppException
from lib.core.reporter import Reporter
from lib.core.response import Response
from lib.core.serviceproviders import BaseServiceProvider
from lib.core.usecases import BaseReportableUseCase


class GetIntegrations(BaseReportableUseCase):
    def __init__(self, reporter: Reporter, service_provider: BaseServiceProvider):

        super().__init__(reporter)
        self._service_provider = service_provider

    def execute(self) -> Response:
        integrations = self._service_provider.integrations.list().data
        integrations = list(sorted(integrations, key=lambda x: x.createdAt))
        integrations.reverse()
        self._response.data = integrations
        return self._response


class AttachIntegrations(BaseReportableUseCase):
    def __init__(
        self,
        reporter: Reporter,
        project: ProjectEntity,
        folder: FolderEntity,
        service_provider: BaseServiceProvider,
        integration: IntegrationEntity,
        folder_path: str = None,
    ):

        super().__init__(reporter)
        self._project = project
        self._folder = folder
        self._integration = integration
        self._service_provider = service_provider
        self._folder_path = folder_path

    @property
    def _upload_path(self):
        return f"{self._project.name}{f'/{self._folder.name}' if self._folder.name != 'root' else ''}"

    def execute(self) -> Response:
        integrations: List[
            IntegrationEntity
        ] = self._service_provider.integrations.list().data
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
            attached = self._service_provider.integrations.attach_items(
                project=self._project,
                folder=self._folder,
                integration=integration,
                folder_name=self._folder_path,
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
