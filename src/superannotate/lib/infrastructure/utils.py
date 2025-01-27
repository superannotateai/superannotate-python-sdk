import time
from itertools import islice
from pathlib import Path
from typing import Dict
from typing import List
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
        self._custom_fields_name_id_map: Dict[int, Dict[str, int]] = {}
        self._custom_fields_id_name_map: Dict[int, Dict[int, str]] = {}
        self._custom_fields_id_component_id_map: Dict[int, Dict[int, int]] = {}
        self._cache_timestamps: Dict[
            int, Dict[str, float]
        ] = {}  # Tracking separate timestamps for roles and statuses

    def _is_cache_valid(
        self, cache_key: int, cache_type: Literal["statuses", "roles", "custom_fields"]
    ) -> bool:
        current_time = time.time()
        if (
            cache_key in self._cache_timestamps
            and cache_type in self._cache_timestamps[cache_key]
        ):
            return (
                current_time - self._cache_timestamps[cache_key][cache_type]
                < self.ttl_seconds
            )
        return False

    def _update_cache_timestamp(self, cache_key: int, cache_type: str):
        if cache_key not in self._cache_timestamps:
            self._cache_timestamps[cache_key] = {}
        self._cache_timestamps[cache_key][cache_type] = time.time()

    def _sync_roles(self, project: entities.ProjectEntity):
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
        self._update_cache_timestamp(cache_key=project.id, cache_type="roles")

    def _sync_statuses(self, project: entities.ProjectEntity):
        response = self.work_management.list_workflow_statuses(
            project.id, project.workflow_id
        )
        if not response.ok:
            raise AppException(response.error)
        statuses = response.data["data"]
        status_name_value_map = {
            status["status"]["name"]: status["value"] for status in statuses
        }
        self._annotation_status_name_value_mapping[project.id] = status_name_value_map
        self._annotation_status_value_name_mapping[project.id] = {
            v: k for k, v in status_name_value_map.items()
        }
        self._update_cache_timestamp(cache_key=project.id, cache_type="statuses")

    def _sync_project_data(
        self, project: entities.ProjectEntity, data_type: Literal["statuses", "roles"]
    ):
        if data_type == "roles" and not self._is_cache_valid(
            cache_key=project.id, cache_type="roles"
        ):
            self._sync_roles(project)
        elif data_type == "statuses" and not self._is_cache_valid(
            cache_key=project.id, cache_type="statuses"
        ):
            self._sync_statuses(project)

    def get_role_id(self, project: entities.ProjectEntity, role_name: str) -> int:
        self._sync_project_data(project, "roles")
        mapping = self._role_name_id_map.get(project.id, {})
        if role_name in mapping:
            return mapping[role_name]
        raise AppException("Invalid assignments role provided.")

    def get_role_name(self, project: entities.ProjectEntity, role_id: int) -> str:
        self._sync_project_data(project, "roles")
        mapping = self._role_id_name_map.get(project.id, {})
        if role_id in mapping:
            return mapping[role_id]
        raise AppException("Invalid assignments role provided.")

    def get_annotation_status_value(
        self, project: entities.ProjectEntity, status_name: str
    ) -> int:
        self._sync_project_data(project, "statuses")
        mapping = self._annotation_status_name_value_mapping.get(project.id, {})
        if status_name in mapping:
            return mapping[status_name]
        raise AppException("Invalid status provided.")

    def get_annotation_status_name(
        self, project: entities.ProjectEntity, status_value: int
    ) -> str:
        self._sync_project_data(project, "statuses")
        mapping = self._annotation_status_value_name_mapping.get(project.id, {})
        if status_value in mapping:
            return mapping[status_value]
        raise AppException("Invalid status provided.")

    def _sync_project_custom_fields(self, team_id: int):
        if not self._is_cache_valid(cache_key=team_id, cache_type="custom_fields"):
            res = self.work_management.list_project_custom_field_templates()
            if not res.ok:
                raise AppException(res.error)
            self._custom_fields_name_id_map[team_id] = {
                i["name"]: i["id"] for i in res.data["data"]
            }
            self._custom_fields_id_name_map[team_id] = {
                i["id"]: i["name"] for i in res.data["data"]
            }
            self._custom_fields_id_component_id_map[team_id] = {
                i["id"]: i["component_id"] for i in res.data["data"]
            }
            self._update_cache_timestamp(cache_key=team_id, cache_type="custom_fields")

    def get_project_custom_field_id(self, team_id: int, field_name: str):
        self._sync_project_custom_fields(team_id)
        mapping = self._custom_fields_name_id_map.get(team_id, {})
        if field_name in mapping:
            return mapping[field_name]
        raise AppException("Invalid custom field name provided.")

    def get_project_custom_field_name(self, team_id: int, field_id: int):
        self._sync_project_custom_fields(team_id)
        mapping = self._custom_fields_id_name_map.get(team_id, {})
        if field_id in mapping:
            return mapping[field_id]
        raise AppException("Invalid custom field ID provided.")

    def get_project_custom_field_component_id(self, team_id: int, field_id: int):
        self._sync_project_custom_fields(team_id)
        mapping = self._custom_fields_id_component_id_map.get(team_id, {})
        if field_id in mapping:
            return mapping[field_id]
        raise AppException("Invalid custom field ID provided.")

    def list_project_custom_field_names(self, team_id: int) -> List[str]:
        self._sync_project_custom_fields(team_id)
        return list(self._custom_fields_name_id_map.get(team_id, {}).keys())
