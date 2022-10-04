from typing import List

import lib.core as constances
from lib.core.conditions import Condition
from lib.core.conditions import CONDITION_EQ as EQ
from lib.core.entities import FolderEntity
from lib.core.entities import ProjectEntity
from lib.core.exceptions import AppException
from lib.core.exceptions import AppValidationException
from lib.core.repositories import BaseManageableRepository
from lib.core.serviceproviders import BaseServiceProvider
from lib.core.serviceproviders import SuperannotateServiceProvider
from lib.core.usecases.base import BaseUseCase
from superannotate.logger import get_default_logger

logger = get_default_logger()


class CreateFolderUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        folder: FolderEntity,
        service_provider: BaseServiceProvider,
    ):
        super().__init__()
        self._project = project
        self._folder = folder
        self._service_provider = service_provider
        self._origin_name = folder.name

    def validate_folder(self):
        if not self._folder.name:
            raise AppValidationException("Folder name cannot be empty.")
        if (
            len(
                set(self._folder.name).intersection(
                    constances.SPECIAL_CHARACTERS_IN_PROJECT_FOLDER_NAMES
                )
            )
            > 0
        ):
            self._folder.name = "".join(
                "_"
                if char in constances.SPECIAL_CHARACTERS_IN_PROJECT_FOLDER_NAMES
                else char
                for char in self._folder.name
            )
            logger.warning(
                "New folder name has special characters. Special characters will be replaced by underscores."
            )

    def execute(self):
        if self.is_valid():
            self._folder.project_id = self._project.id
            self._response.data = self._service_provider.folders.create(
                self._project, self._folder
            ).data
            if self._response.data.name not in (self._origin_name, self._folder.name):
                logger.warning(
                    f"Created folder has name {self._response.data.name},"
                    f" since folder with name {self._folder.name} already existed."
                )
        return self._response


class GetFolderUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        service_provider: BaseServiceProvider,
        folder_name: str,
    ):
        super().__init__()
        self._project = project
        self._service_provider = service_provider
        self._folder_name = folder_name

    def execute(self):
        try:
            self._response.data = self._service_provider.folders.get_by_name(
                self._project, self._folder_name
            ).data
        except AppException as e:
            self._response.errors = e
        return self._response


class SearchFoldersUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        service_provider: BaseServiceProvider,
        condition: Condition,
    ):
        super().__init__()
        self._project = project
        self._service_provider = service_provider
        self._condition = condition

    def execute(self):
        condition = Condition("project_id", self._project.id, EQ)
        if self._condition:
            condition &= self._condition
        self._response.data = self._service_provider.folders.list(condition).data
        return self._response


class DeleteFolderUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        folders: List[FolderEntity],
        service_provider: BaseServiceProvider,
    ):
        super().__init__()
        self._project = project
        self._folders = folders
        self.service_provider = service_provider

    def execute(self):
        if self._folders:
            response = self.service_provider.folders.delete_multiple(
                self._project, self._folders
            )
            if not response.ok:
                self._response.errors = AppException("Couldn't delete folders.")
        else:
            self._response.errors = AppException("There is no folder to delete.")
        return self._response


class UpdateFolderUseCase(BaseUseCase):
    def __init__(
        self,
        folders: BaseManageableRepository,
        folder: FolderEntity,
    ):
        super().__init__()
        self._folders = folders
        self._folder = folder

    def validate_folder(self):
        if not self._folder.name:
            raise AppValidationException("Folder name cannot be empty.")
        if (
            len(
                set(self._folder.name).intersection(
                    constances.SPECIAL_CHARACTERS_IN_PROJECT_FOLDER_NAMES
                )
            )
            > 0
        ):
            self._folder.name = "".join(
                "_"
                if char in constances.SPECIAL_CHARACTERS_IN_PROJECT_FOLDER_NAMES
                else char
                for char in self._folder.name
            )
            logger.warning(
                "New folder name has special characters. Special characters will be replaced by underscores."
            )

    def execute(self):
        if self.is_valid():
            folder = self._folders.update(self._folder)
            if not folder:
                self._response.errors = AppException("Couldn't rename folder.")
            self._response.data = folder
        return self._response


class AssignFolderUseCase(BaseUseCase):
    def __init__(
        self,
        service: SuperannotateServiceProvider,
        project_entity: ProjectEntity,
        folder: FolderEntity,
        users: List[str],
    ):
        super().__init__()
        self._service = service
        self._project_entity = project_entity
        self._folder = folder
        self._users = users

    def execute(self):
        is_assigned = self._service.assign_folder(
            team_id=self._project_entity.team_id,
            project_id=self._project_entity.id,
            folder_name=self._folder.name,
            users=self._users,
        )
        if is_assigned:
            logger.info(
                f'Assigned {self._folder.name} to users: {", ".join(self._users)}'
            )
        else:
            self._response.errors = AppException(
                f"Couldn't assign folder to users: {', '.join(self._users)}"
            )
        return self._response
