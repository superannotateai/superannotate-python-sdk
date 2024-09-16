import time
from itertools import islice
from pathlib import Path
from typing import Dict
from typing import Literal
from typing import Optional
from typing import Tuple
from typing import Union

from lib.core import entities
from lib.core.exceptions import AppException
from lib.core.exceptions import PathError
from lib.infrastructure.services.work_management import WorkManagementService


def divide_to_chunks(it, size):
    it = iter(it)
    return iter(lambda: tuple(islice(it, size)), ())


def split_project_path(project_path: str) -> Tuple[str, Optional[str]]:
    path = Path(project_path)
    if len(path.parts) > 3:
        raise PathError("There can be no sub folders in the project")
    elif len(path.parts) == 2:
        project_name, folder_name = path.parts
    else:
        project_name, folder_name = path.name, ""

    return project_name, folder_name


def extract_project_folder(user_input: Union[str, dict]) -> Tuple[str, Optional[str]]:
    if isinstance(user_input, str):
        return split_project_path(user_input)
    if isinstance(user_input, dict):
        project_path = user_input.get("name")
        if not project_path:
            raise PathError("Invalid project path")
        return split_project_path(user_input["name"])
    raise PathError("Invalid project path")


class CachedWorkManagementRepository:
    def __init__(self, ttl_seconds: int, work_management: WorkManagementService):
        self.ttl_seconds = ttl_seconds
        self.work_management = work_management
        self._annotation_status_name_value_mapping: Dict[int, Dict[str, int]] = {}
        self._annotation_status_value_name_mapping: Dict[int, Dict[int, str]] = {}
        self._role_name_id_map: Dict[int, Dict[str, int]] = {}
        self._role_id_name_map: Dict[int, Dict[int, str]] = {}
        self._cache_timestamps: Dict[
            int, Dict[str, float]
        ] = {}  # Tracking separate timestamps for roles and statuses

    def _is_cache_valid(
        self, project_id: int, cache_type: Literal["statuses", "roles"]
    ) -> bool:
        current_time = time.time()
        if (
            project_id in self._cache_timestamps
            and cache_type in self._cache_timestamps[project_id]
        ):
            return (
                current_time - self._cache_timestamps[project_id][cache_type]
                < self.ttl_seconds
            )
        return False

    def _update_cache_timestamp(self, project_id: int, cache_type: str):
        if project_id not in self._cache_timestamps:
            self._cache_timestamps[project_id] = {}
        self._cache_timestamps[project_id][cache_type] = time.time()

    def _sync_data(
        self, project: entities.ProjectEntity, data_type: Literal["statuses", "roles"]
    ):
        if data_type == "roles":
            response = self.work_management.list_workflow_roles(
                project.id, project.workflow_id
            )
            if not response.ok:
                raise AppException(response.error)
            roles = response.data["data"]
            self._role_name_id_map[project.id] = {
                role["role"]["name"]: role["role_id"] for role in roles
            }
            self._role_id_name_map[project.id] = {
                role["role_id"]: role["role"]["name"] for role in roles
            }
            self._role_id_name_map[project.id][3] = "Admin"
            self._role_name_id_map[project.id]["Admin"] = 3
            self._update_cache_timestamp(project.id, "roles")

        elif data_type == "statuses":
            response = self.work_management.list_workflow_statuses(
                project.id, project.workflow_id
            )
            if not response.ok:
                raise AppException(response.error)
            statuses = response.data["data"]
            status_name_value_map = {
                status["status"]["name"]: status["value"] for status in statuses
            }
            self._annotation_status_name_value_mapping[
                project.id
            ] = status_name_value_map
            self._annotation_status_value_name_mapping[project.id] = {
                v: k for k, v in status_name_value_map.items()
            }
            self._update_cache_timestamp(project.id, "statuses")

    def _sync(
        self, project: entities.ProjectEntity, data_type: Literal["statuses", "roles"]
    ):
        if data_type == "roles" and not self._is_cache_valid(project.id, "roles"):
            self._sync_data(project, "roles")
        elif data_type == "statuses" and not self._is_cache_valid(
            project.id, "statuses"
        ):
            self._sync_data(project, "statuses")

    def get_role_id(self, project: entities.ProjectEntity, role_name: str) -> int:
        self._sync(project, "roles")
        mapping = self._role_name_id_map.get(project.id, {})
        if role_name in mapping:
            return mapping[role_name]
        raise AppException("Invalid assignments role provided.")

    def get_role_name(self, project: entities.ProjectEntity, role_id: int) -> str:
        self._sync(project, "roles")
        mapping = self._role_id_name_map.get(project.id, {})
        if role_id in mapping:
            return mapping[role_id]
        raise AppException("Invalid assignments role provided.")

    def get_annotation_status_value(
        self, project: entities.ProjectEntity, status_name: str
    ) -> int:
        self._sync(project, "statuses")
        mapping = self._annotation_status_name_value_mapping.get(project.id, {})
        if status_name in mapping:
            return mapping[status_name]
        raise AppException("Invalid status provided.")

    def get_annotation_status_name(
        self, project: entities.ProjectEntity, status_value: int
    ) -> str:
        self._sync(project, "statuses")
        mapping = self._annotation_status_value_name_mapping.get(project.id, {})
        if status_value in mapping:
            return mapping[status_value]
        raise AppException("Invalid status provided.")
