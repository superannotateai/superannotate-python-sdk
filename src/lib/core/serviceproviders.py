from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import Dict
from typing import List


class SuerannotateServiceProvider(ABC):
    @abstractmethod
    def create_image(
        self,
        project_id: int,
        team_id: int,
        images: List[Dict],
        annotation_status_code: int,
        upload_state_code: int,
        meta: Dict[Any],
        annotation_json_path: str,
        annotation_bluemap_path: str,
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
