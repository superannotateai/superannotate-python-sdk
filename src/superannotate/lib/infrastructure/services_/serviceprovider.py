from lib.core import entities
from lib.core.service_types import UserLimitsResponse
from lib.core.serviceproviders import BaseServiceProvider
from lib.infrastructure.services_.annotation_class import AnnotationClassService
from lib.infrastructure.services_.folder import FolderService
from lib.infrastructure.services_.http_client import HttpClient
from lib.infrastructure.services_.item import ItemService
from lib.infrastructure.services_.project import ProjectService


class ServiceProvider(BaseServiceProvider):
    URL_GET_LIMITS = "project/{project_id}/limitationDetails"

    def __init__(self, client: HttpClient):
        self.client = client
        self.projects = ProjectService(client)
        self.folders = FolderService(client)
        self.items = ItemService(client)
        self.annotation_classes = AnnotationClassService(client)

    def get_limitations(
        self, project: entities.ProjectEntity, folder: entities.FolderEntity
    ):
        return self.client.request(
            self.URL_GET_LIMITS.format(project_id=project.id),
            "get",
            params={"folder_id": folder.id},
            content_type=UserLimitsResponse,
        )
