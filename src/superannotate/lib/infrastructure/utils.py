import asyncio
import logging
import time
import typing
from abc import ABC
from abc import abstractmethod
from functools import wraps
from itertools import islice
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Tuple
from typing import Type
from typing import Union

from lib.core.entities import ProjectEntity
from lib.core.enums import CustomFieldEntityEnum
from lib.core.exceptions import AppException
from lib.core.exceptions import PathError
from lib.infrastructure.services.work_management import WorkManagementService


logger = logging.getLogger("sa")


class EntityContext(typing.TypedDict, total=False):
    team_id: int
    project_id: Optional[int]


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


def async_retry_on_generator(
    exceptions: Tuple[Type[Exception]],
    retries: int = 3,
    delay: float = 0.3,
    backoff: float = 0.3,
):
    """
    An async retry decorator that retries a function only on specific exceptions.

    Parameters:
        exceptions (tuple): Tuple of exception classes to retry on.
        retries (int): Number of retry attempts.
        delay (float): Initial delay between retries in seconds.
        backoff (float): Factor to increase the delay after each failure.
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay
            raised_exception = None

            while attempt < retries:
                try:
                    async for v in func(*args, **kwargs):
                        yield v
                    return
                except exceptions as e:
                    raised_exception = e
                    logger.debug(
                        f"Attempt {attempt + 1}/{retries} failed with error: {e}. "
                        f"Retrying in {current_delay} seconds..."
                    )
                    await asyncio.sleep(current_delay)
                    current_delay += backoff  # Exponential backoff
                finally:
                    attempt += 1
            if raised_exception:
                logger.error(
                    f"All {retries} attempts failed due to {raised_exception}."
                )
                raise raised_exception

        return wrapper

    return decorator


def annotation_is_valid(annotation: dict) -> bool:
    annotation_keys = annotation.keys()
    if (
        "errors" in annotation_keys
        or "error" in annotation_keys
        or "metadata" not in annotation_keys
    ):
        return False
    return True


class BaseCachedWorkManagementRepository(ABC):
    def __init__(self, ttl_seconds: int, work_management: WorkManagementService):
        self.ttl_seconds = ttl_seconds
        self.work_management = work_management
        self._K_V_map = {}
        self._cache_timestamps: Dict[Any, float] = {}

    def _update_cache_timestamp(self, key):
        self._cache_timestamps[key] = time.time()

    def _is_cache_valid(self, key):
        current_time = time.time()
        return key in self._cache_timestamps and (
            current_time - self._cache_timestamps[key] < self.ttl_seconds
        )

    @abstractmethod
    def sync(self, **kwargs):
        raise NotImplementedError

    def get(self, key, **kwargs):
        if not self._is_cache_valid(key):
            self.sync(**kwargs)
        return self._K_V_map[key]


class CategoryCache(BaseCachedWorkManagementRepository):
    def sync(self, project: ProjectEntity):
        response = self.work_management.list_project_categories(project.id)
        if not response.ok:
            raise AppException(response.error)
        categories = response.data
        self._K_V_map[project.id] = {
            "category_name_id_map": {
                category.value: category.id for category in categories
            },
            "category_id_name_map": {
                category.id: category.value for category in categories
            },
        }
        self._update_cache_timestamp(project.id)


class RoleCache(BaseCachedWorkManagementRepository):
    def sync(self, project: ProjectEntity):
        response = self.work_management.list_workflow_roles(
            project.id, project.workflow_id
        )
        if not response.ok:
            raise AppException(response.error)
        roles = response.data["data"]
        self._K_V_map[project.id] = {
            "role_name_id_map": {
                **{role["role"]["name"]: role["role_id"] for role in roles},
                "ProjectAdmin": 3,
            },
            "role_id_name_map": {
                **{role["role_id"]: role["role"]["name"] for role in roles},
                3: "ProjectAdmin",
            },
        }
        self._update_cache_timestamp(project.id)


class StatusCache(BaseCachedWorkManagementRepository):
    def sync(self, project):
        response = self.work_management.list_workflow_statuses(
            project.id, project.workflow_id
        )
        if not response.ok:
            raise AppException(response.error)
        statuses = response.data["data"]
        status_name_value_map = {
            status["status"]["name"]: status["value"] for status in statuses
        }
        status_value_name_map = {v: k for k, v in status_name_value_map.items()}
        self._K_V_map[project.id] = {
            "status_name_value_map": status_name_value_map,
            "status_value_name_map": status_value_name_map,
        }
        self._update_cache_timestamp(project.id)


class CustomFieldCache(BaseCachedWorkManagementRepository):
    def __init__(
        self,
        ttl_seconds: int,
        work_management: WorkManagementService,
        entity: CustomFieldEntityEnum,
        parent_entity: CustomFieldEntityEnum,
    ):
        super().__init__(ttl_seconds, work_management)
        self._entity = entity
        self._parent_entity = parent_entity

    def sync(self, team_id):
        response = self.work_management.list_custom_field_templates(
            entity=self._entity, parent_entity=self._parent_entity
        )
        if not response.ok:
            raise AppException(response.error)
        custom_fields_name_id_map = {
            field["name"]: field["id"] for field in response.data["data"]
        }
        custom_fields_id_name_map = {
            field["id"]: field["name"] for field in response.data["data"]
        }
        custom_fields_id_component_id_map = {
            field["id"]: field["component_id"] for field in response.data["data"]
        }
        self._K_V_map[team_id] = {
            "custom_fields_name_id_map": custom_fields_name_id_map,
            "custom_fields_id_name_map": custom_fields_id_name_map,
            "custom_fields_id_component_id_map": custom_fields_id_component_id_map,
            "templates": response.data["data"],
        }
        self._update_cache_timestamp(team_id)

    def get(self, key, **kwargs):
        if not self._is_cache_valid(key):
            self.sync(team_id=key)
        return self._K_V_map[key]


class ProjectUserCustomFieldCache(CustomFieldCache):
    def sync(self, project_id):
        response = self.work_management.list_custom_field_templates(
            entity=self._entity,
            parent_entity=self._parent_entity,
            context={"project_id": project_id},
        )
        if not response.ok:
            raise AppException(response.error)
        custom_fields_name_id_map = {
            field["name"]: field["id"] for field in response.data["data"]
        }
        custom_fields_id_name_map = {
            field["id"]: field["name"] for field in response.data["data"]
        }
        custom_fields_id_component_id_map = {
            field["id"]: field["component_id"] for field in response.data["data"]
        }
        self._K_V_map[project_id] = {
            "custom_fields_name_id_map": custom_fields_name_id_map,
            "custom_fields_id_name_map": custom_fields_id_name_map,
            "custom_fields_id_component_id_map": custom_fields_id_component_id_map,
            "templates": response.data["data"],
        }
        self._update_cache_timestamp(project_id)

    def get(self, key, **kwargs):
        if not self._is_cache_valid(key):
            self.sync(project_id=key)
        return self._K_V_map[key]


class CachedWorkManagementRepository:
    def __init__(self, ttl_seconds: int, work_management):
        self._category_cache = CategoryCache(ttl_seconds, work_management)
        self._role_cache = RoleCache(ttl_seconds, work_management)
        self._status_cache = StatusCache(ttl_seconds, work_management)
        self._project_custom_field_cache = CustomFieldCache(
            ttl_seconds,
            work_management,
            CustomFieldEntityEnum.PROJECT,
            CustomFieldEntityEnum.TEAM,
        )
        self._team_user_custom_field_cache = CustomFieldCache(
            ttl_seconds,
            work_management,
            CustomFieldEntityEnum.CONTRIBUTOR,
            CustomFieldEntityEnum.TEAM,
        )
        self._project_user_custom_field_cache = ProjectUserCustomFieldCache(
            ttl_seconds,
            work_management,
            CustomFieldEntityEnum.CONTRIBUTOR,
            CustomFieldEntityEnum.PROJECT,
        )

    def get_category_id(self, project, category_name: str) -> int:
        data = self._category_cache.get(project.id, project=project)
        if category_name in data["category_name_id_map"]:
            return data["category_name_id_map"][category_name]
        raise AppException("Invalid category provided.")

    def get_role_id(self, project, role_name: str) -> int:
        role_data = self._role_cache.get(project.id, project=project)
        if role_name in role_data["role_name_id_map"]:
            return role_data["role_name_id_map"][role_name]
        raise AppException("Invalid assignments role provided.")

    def get_role_name(self, project, role_id: int) -> str:
        role_data = self._role_cache.get(project.id, project=project)
        if role_id in role_data["role_id_name_map"]:
            return role_data["role_id_name_map"][role_id]
        raise AppException("Invalid role ID provided.")

    def get_annotation_status_value(self, project, status_name: str) -> int:
        status_data = self._status_cache.get(project.id, project=project)
        if status_name in status_data["status_name_value_map"]:
            return status_data["status_name_value_map"][status_name]
        raise AppException("Invalid status provided.")

    def get_annotation_status_name(self, project, status_value: int) -> str:
        status_data = self._status_cache.get(project.id, project=project)
        if status_value in status_data["status_value_name_map"]:
            return status_data["status_value_name_map"][status_value]
        raise AppException("Invalid status value provided.")

    def get_custom_field_id(
        self,
        context: EntityContext,
        field_name: str,
        entity: CustomFieldEntityEnum,
        parent: CustomFieldEntityEnum,
    ) -> int:
        if entity == CustomFieldEntityEnum.PROJECT:
            custom_field_data = self._project_custom_field_cache.get(context["team_id"])
        else:
            if parent == CustomFieldEntityEnum.TEAM:
                custom_field_data = self._team_user_custom_field_cache.get(
                    context["team_id"]
                )
            else:
                custom_field_data = self._project_user_custom_field_cache.get(
                    context["project_id"]
                )
        if field_name in custom_field_data["custom_fields_name_id_map"]:
            return custom_field_data["custom_fields_name_id_map"][field_name]
        raise AppException("Invalid custom field name provided.")

    def get_custom_field_name(
        self,
        context: EntityContext,
        field_id: int,
        entity: CustomFieldEntityEnum,
        parent: CustomFieldEntityEnum,
    ) -> str:
        if entity == CustomFieldEntityEnum.PROJECT:
            custom_field_data = self._project_custom_field_cache.get(context["team_id"])
        else:
            if parent == CustomFieldEntityEnum.TEAM:
                custom_field_data = self._team_user_custom_field_cache.get(
                    context["team_id"]
                )
            else:
                custom_field_data = self._project_user_custom_field_cache.get(
                    context["project_id"]
                )
        if field_id in custom_field_data["custom_fields_id_name_map"]:
            return custom_field_data["custom_fields_id_name_map"][field_id]
        raise AppException("Invalid custom field ID provided.")

    def get_custom_field_component_id(
        self,
        context: EntityContext,
        field_id: int,
        entity: CustomFieldEntityEnum,
        parent: CustomFieldEntityEnum,
    ) -> str:
        if entity == CustomFieldEntityEnum.PROJECT:
            custom_field_data = self._project_custom_field_cache.get(context["team_id"])
        else:
            if parent == CustomFieldEntityEnum.TEAM:
                custom_field_data = self._team_user_custom_field_cache.get(
                    context["team_id"]
                )
            else:
                custom_field_data = self._project_user_custom_field_cache.get(
                    context["project_id"]
                )
        if field_id in custom_field_data["custom_fields_id_component_id_map"]:
            return custom_field_data["custom_fields_id_component_id_map"][field_id]
        raise AppException("Invalid custom field ID provided.")

    def list_custom_field_names(
        self,
        context: EntityContext,
        entity: CustomFieldEntityEnum,
        parent: CustomFieldEntityEnum,
    ) -> list:
        if entity == CustomFieldEntityEnum.PROJECT:
            custom_field_data = self._project_custom_field_cache.get(context["team_id"])
        else:
            if parent == CustomFieldEntityEnum.TEAM:
                custom_field_data = self._team_user_custom_field_cache.get(
                    context["team_id"]
                )
            else:
                custom_field_data = self._project_user_custom_field_cache.get(
                    context["project_id"]
                )
        return list(custom_field_data["custom_fields_name_id_map"].keys())

    def list_templates(
        self,
        context: EntityContext,
        entity: CustomFieldEntityEnum,
        parent: CustomFieldEntityEnum,
    ):
        if entity == CustomFieldEntityEnum.PROJECT:
            return self._project_custom_field_cache.get(context["team_id"])["templates"]
        elif entity == CustomFieldEntityEnum.CONTRIBUTOR:
            if parent == CustomFieldEntityEnum.TEAM:
                return self._team_user_custom_field_cache.get(context["team_id"])[
                    "templates"
                ]
            else:
                return self._project_user_custom_field_cache.get(context["project_id"])[
                    "templates"
                ]
        raise AppException("Invalid entity provided.")
