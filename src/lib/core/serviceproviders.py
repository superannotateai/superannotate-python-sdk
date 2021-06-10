from abc import ABC
from abc import abstractmethod
from typing import List
from typing import Dict
from typing import Any


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
            annotation_bluemap_path: str
    ):
        raise NotImplementedError

