import src.lib.core as constances
from src.lib.core.conditions import Condition
from src.lib.core.conditions import CONDITION_EQ as EQ
from src.lib.core.entities import ProjectEntity
from src.lib.core.exceptions import AppException
from src.lib.core.response import Response
from src.lib.core.usecases import CreateProjectUseCase
from src.lib.core.usecases import DeleteProjectUseCase
from src.lib.core.usecases import GetProjectsUseCase
from src.lib.core.usecases import UpdateProjectUseCase
from src.lib.infrastructure.repositories import ConfigRepository
from src.lib.infrastructure.repositories import ProjectRepository
from src.lib.infrastructure.services import SuperannotateBackendService


class BaseController:
    def __init__(self, backend_client: SuperannotateBackendService, response: Response):
        self._backend_client = backend_client
        self._response = response

    @property
    def response(self):
        return self._response

    @property
    def projects(self):
        return ProjectRepository(self._backend_client)

    @property
    def configs(self):
        return ConfigRepository()

    @property
    def team_id(self) -> str:
        return self.configs.get_one("token").value.split("=")[-1]


class Controller(BaseController):
    def search_project(self, name: str) -> Response:
        use_case = GetProjectsUseCase(
            self.response, Condition("project_name", name, EQ), self.projects
        )
        use_case.execute()
        return self.response

    def create_project(
        self, name: str, description: str, project_type: str
    ) -> Response:
        project_type = constances.ProjectType[project_type.upper()].value
        entity = ProjectEntity(
            name=name, description=description, project_type=project_type
        )
        use_case = CreateProjectUseCase(self.response, entity, self.projects)
        use_case.execute()
        return self.response

    def delete_project(self, name: str):
        entities = self.projects.get_all(
            Condition("teams_id", self.team_id, EQ) & Condition("name", name, EQ)
        )
        if entities and len(entities) == 1:
            use_case = DeleteProjectUseCase(self.response, entities[0], self.projects)
            use_case.execute()
            return self.response
        raise AppException("There are duplicated names.")

    def rename_project(self, name: str, new_name: str) -> Response:
        entities = self.projects.get_all(
            Condition("teams_id", self.team_id, EQ) & Condition("name", name, EQ)
        )
        if entities and len(entities) == 1:
            entity = entities[0]
            entity.name = new_name
            use_case = UpdateProjectUseCase(self.response, entity, self.projects)
            use_case.execute()
            return self.response
        raise AppException("There are duplicated names.")

    def clone_project(
        self,
        name: str,
        from_name: str,
        project_description: str,
        copy_annotation_classes=True,
        copy_settings=True,
        copy_workflow=True,
        copy_contributors=False,
    ):
        raise NotImplementedError

    def get_project_metadata(
        self,
        name: str,
        include_annotation_classes=False,
        include_settings=False,
        include_workflow=False,
        include_contributors=False,
        include_complete_image_count=False,
    ):
        raise NotImplementedError

    def create_project_from_metadata(self):
        # todo move to cli level
        raise NotImplementedError
