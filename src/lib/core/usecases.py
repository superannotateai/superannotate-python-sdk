from abc import ABC
from abc import abstractmethod

from src.lib.core.conditions import Condition
from src.lib.core.conditions import CONDITION_EQ as EQ
from src.lib.core.entities import ProjectEntity
from src.lib.core.exceptions import AppValidationException
from src.lib.core.repositories import BaseManageableRepository
from src.lib.core.response import Response


class BaseUseCase(ABC):
    def __init__(self, response: Response):
        self._response = response

    @abstractmethod
    def execute(self):
        raise NotImplementedError

    def validate(self):
        for name in dir(self):
            if name.startswith("validate_"):
                method = getattr(self, name)
                method()


class GetProjectsUseCase(BaseUseCase):
    def __init__(
        self,
        response: Response,
        condition: Condition,
        projects: BaseManageableRepository,
    ):
        super().__init__(response)
        self._condition = condition
        self._projects = projects

    def execute(self):
        self._response.data = self._projects.get_all(self._condition)


class CreateProjectUseCase(BaseUseCase):
    def __init__(
        self,
        response: Response,
        project: ProjectEntity,
        projects: BaseManageableRepository,
    ):

        super().__init__(response)
        self._project = project
        self._projects = projects

    def execute(self):
        self._projects.insert(self._project)

    def validate_project_name_uniqueness(self):
        condition = Condition("name", self._project.name, EQ) & Condition(
            "team_id", self._project.team_id, EQ
        )
        if self._projects.get_all(condition):
            raise AppValidationException(
                f"Project name {self._project.name} is not unique. "
                f"To use SDK please make project names unique."
            )


class DeleteProjectUseCase(BaseUseCase):
    def __init__(
        self,
        response: Response,
        project: ProjectEntity,
        projects: BaseManageableRepository,
    ):

        super().__init__(response)
        self._project = project
        self._projects = projects

    def execute(self):
        self._projects.delete(self._project.uuid)


class UpdateProjectUseCase(BaseUseCase):
    def __init__(
        self,
        response: Response,
        project: ProjectEntity,
        projects: BaseManageableRepository,
    ):

        super().__init__(response)
        self._project = project
        self._projects = projects

    def execute(self):
        self._projects.update(self._project)
