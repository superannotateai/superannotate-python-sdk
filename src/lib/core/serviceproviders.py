from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import Dict
from typing import Iterable
from typing import List


class SuerannotateServiceProvider(ABC):
    @abstractmethod
    def attach_files(
        self,
        project_id: int,
        team_id: int,
        files: List[Dict],
        annotation_status_code: int,
        upload_state_code: int,
        meta: Dict
    ):
        raise NotImplementedError

    @abstractmethod
    def get_annotation_classes(
        self, project_id: int, team_id: int, name_prefix: str = None
    ):
        raise NotImplementedError

    @abstractmethod
    def share_project(
        self, project_id: int, team_id: int, user_id: int, user_role: int
    ):
        raise NotImplementedError

    @abstractmethod
    def prepare_export(
        self,
        project_id: int,
        team_id: int,
        folders: List[str],
        annotation_statuses: Iterable[Any],
        include_fuse: bool,
        only_pinned: bool,
    ):
        raise NotImplementedError

    @abstractmethod
    def invite_contributor(self, team_id: int, email: str, user_role: str):
        raise NotImplementedError

    @abstractmethod
    def delete_team_invitation(self, team_id: int, token: str, email: str):
        raise NotImplementedError

    @abstractmethod
    def search_team_contributors(self, team_id: int, query_string: str = None):
        raise NotImplementedError

    @abstractmethod
    def get_project_settings(self, project_id: int, team_id: int):
        raise NotImplementedError

    @abstractmethod
    def set_project_settings(self, project_id: int, team_id: int, data: Dict):
        raise NotImplementedError

    @abstractmethod
    def get_project_workflows(self, project_id: int, team_id: int):
        raise NotImplementedError

    @abstractmethod
    def set_project_workflow(self, project_id: int, team_id: int, data: Dict):
        raise NotImplementedError
