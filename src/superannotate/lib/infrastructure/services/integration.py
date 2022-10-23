from lib.core import entities
from lib.core.service_types import IntegrationResponse
from lib.core.serviceproviders import BaseIntegrationService


class IntegrationService(BaseIntegrationService):
    URL_LIST = "integrations"
    URL_ATTACH_INTEGRATIONS = "image/integration/create"

    def list(self):

        res = self.client.request(
            self.URL_LIST,
            "get",
            content_type=IntegrationResponse,
            dispatcher=lambda x: x["integrations"],
        )

        return res

    def attach_items(
        self,
        project: entities.ProjectEntity,
        folder: entities.FolderEntity,
        integration: entities.IntegrationEntity,
        folder_name: str = None,
    ):
        data = {
            "team_id": project.team_id,
            "project_id": project.id,
            "folder_id": folder.id,
            "integration_id": integration.id,
        }
        if folder_name:
            data["customer_folder_name"] = folder_name
        return self.client.request(
            self.URL_ATTACH_INTEGRATIONS.format(project.team_id), "post", data=data
        )
