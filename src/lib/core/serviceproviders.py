from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import Dict
from typing import Iterable
from typing import List
from typing import Tuple


class SuerannotateServiceProvider(ABC):
    @abstractmethod
    def attach_files(
        self,
        project_id: int,
        team_id: int,
        files: List[Dict],
        annotation_status_code: int,
        upload_state_code: int,
        meta: Dict,
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

    def delete_folders(self, project_id: int, team_id: int, folder_ids: List[int]):
        raise NotImplementedError

    def get_folder(self, query_string: str):
        raise NotImplementedError

    def get_folders(self, query_string: str = None, params: dict = None):
        raise NotImplementedError

    def create_folder(self, project_id: int, team_id: int, folder_name: str):
        raise NotImplementedError

    def update_folder(self, project_id: int, team_id: int, folder_data: dict):
        raise NotImplementedError

    def get_download_token(
        self,
        project_id: int,
        team_id: int,
        folder_id: int,
        image_id: int,
        include_original: int = 1,
    ) -> dict:
        raise NotImplementedError

    def get_upload_token(
        self, project_id: int, team_id: int, folder_id: int, image_id: int,
    ) -> dict:
        raise NotImplementedError

    def update_image(self, image_id: int, team_id: int, project_id: int, data: dict):
        raise NotImplementedError

    def copy_images_between_folders_transaction(
        self,
        team_id: int,
        project_id: int,
        from_folder_id: int,
        to_folder_id: int,
        images: List[str],
        include_annotations: bool = False,
        include_pin: bool = False,
    ) -> int:
        raise NotImplementedError

    def move_images_between_folders(
        self,
        team_id: int,
        project_id: int,
        from_folder_id: int,
        to_folder_id: int,
        images: List[str],
    ) -> List[str]:
        """
        Returns list of moved images.
        """
        raise NotImplementedError

    def get_duplicated_images(
        self, project_id: int, team_id: int, folder_id: int, images: List[str]
    ):
        raise NotImplementedError

    def get_progress(
        self, project_id: int, team_id: int, poll_id: int
    ) -> Tuple[int, int]:
        raise NotImplementedError

    def set_images_statuses_bulk(
        self,
        image_names: List[str],
        team_id: int,
        project_id: int,
        folder_id: int,
        annotation_status: int,
    ):
        raise NotImplementedError

    def delete_images(self, project_id: int, team_id: int, image_ids: List[int]):
        raise NotImplementedError

    def assign_images(
        self,
        team_id: int,
        project_id: int,
        folder_name: str,
        user: str,
        image_names: list,
    ):
        raise NotImplementedError

    def un_assign_images_url(
        self, team_id: int, project_id: int, folder_name: str, image_names: list,
    ):
        raise NotImplementedError

    def get_bulk_images(
        self, project_id: int, team_id: int, folder_id: int, images: List[str]
    ) -> List[str]:
        raise NotImplementedError

    def un_assign_folder(
        self, team_id: int, project_id: int, folder_name: str,
    ):
        raise NotImplementedError

    def assign_folder(
        self, team_id: int, project_id: int, folder_name: str, users: list
    ):
        raise NotImplementedError

    def un_assign_images(
        self, team_id: int, project_id: int, folder_name: str, image_names: list,
    ):
        raise NotImplementedError
