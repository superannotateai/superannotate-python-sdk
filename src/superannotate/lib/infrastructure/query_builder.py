from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Tuple

from lib.core.entities import BaseItemEntity
from lib.core.entities import ProjectEntity
from lib.core.enums import ApprovalStatus
from lib.core.enums import CustomFieldEntityEnum
from lib.core.enums import CustomFieldType
from lib.core.enums import ProjectStatus
from lib.core.enums import UserRole
from lib.core.enums import WMUserStateEnum
from lib.core.exceptions import AppException
from lib.core.jsx_conditions import EmptyQuery
from lib.core.jsx_conditions import Filter
from lib.core.jsx_conditions import Join
from lib.core.jsx_conditions import OperatorEnum
from lib.core.jsx_conditions import Query
from lib.core.serviceproviders import BaseServiceProvider


def determine_condition_and_key(keys: List[str]) -> Tuple[OperatorEnum, str]:
    """
    Determine the condition and key from the filters.
    """
    if len(keys) == 1:
        return OperatorEnum.EQ, keys[0]
    else:
        if keys[-1].upper() in OperatorEnum.__members__:
            condition = OperatorEnum[keys.pop().upper()]
        else:
            condition = OperatorEnum.EQ
        return condition, ".".join(keys)


class QueryHandler(ABC):
    """Abstract base class for query handlers."""

    @abstractmethod
    def set_next(self, handler: "QueryHandler") -> "QueryHandler":
        pass

    @abstractmethod
    def handle(self, filters: Dict[str, Any], query: Query = None) -> Query:
        """Handle filters and modify the query."""
        pass


class AbstractQueryHandler(QueryHandler):
    """
    The default chaining behavior can be implemented inside a base handler
    class.
    """

    _next_handler: QueryHandler = None

    def set_next(self, handler: QueryHandler) -> QueryHandler:
        self._next_handler = handler
        return handler

    @abstractmethod
    def handle(self, filters: Dict[str, Any], query: Query = None) -> Query:
        if self._next_handler:
            return self._next_handler.handle(filters, query)
        return query


class FieldValidationHandler(AbstractQueryHandler):
    def __init__(self, valid_fields: Iterable[str]):
        self._valid_fields = valid_fields

    def handle(self, filters: Dict[str, Any], query: Query = None) -> Query:
        for param in filters.keys():
            if param not in self._valid_fields:
                raise AppException("Invalid filter param provided.")
        return super().handle(filters, query)


class IncludeHandler(AbstractQueryHandler):
    """Handles include fields in the query."""

    def __init__(self, include: List[str], next_handler: QueryHandler = None):
        if include is None:
            include = []
        self.include = include

    def handle(self, filters: Dict[str, Any], query: Query = None) -> Query:
        assert query is not None, "Query build fail"
        for field in self.include:
            query &= Join(field)
        return super().handle(filters, query)


class ItemFilterHandler(AbstractQueryHandler):
    def __init__(
        self,
        project: ProjectEntity,
        entity: BaseItemEntity,
        service_provider: BaseServiceProvider,
    ):
        self._service_provider = service_provider
        self._entity = entity
        self._project = project

    def handle(self, filters: Dict[str, Any], query: Query = None) -> Query:
        if query is None:
            query = EmptyQuery()
        for key, val in filters.items():
            _keys = key.split("__")
            val = self._handle_special_fields(_keys, val)
            if _keys[0] == "categories" and _keys[1] == "value":
                _keys[1] = "category_id"
            condition, _key = determine_condition_and_key(_keys)
            query &= Filter(_key, val, condition)
        return super().handle(filters, query)

    @staticmethod
    def _extract_value_from_mapping(data, extractor=lambda x: x):
        if isinstance(data, (list, tuple, set)):
            return [extractor(i) for i in data]
        return extractor(data)

    def _handle_special_fields(self, keys: List[str], val):
        """
        Handle special fields like 'approval_status', 'assignments',  'user_role' and 'annotation_status'.
        """
        if keys[0] == "approval_status":
            val = (
                [ApprovalStatus(i).value for i in val]
                if isinstance(val, (list, tuple, set))
                else ApprovalStatus(val).value
            )
        elif keys[0] == "annotation_status":
            val = self._extract_value_from_mapping(
                val,
                lambda x: self._service_provider.get_annotation_status_value(
                    self._project, x
                ),
            )
        elif keys[0] == "assignments" and keys[1] == "user_role":
            if isinstance(val, list):
                val = [
                    self._service_provider.get_role_id(self._project, i) for i in val
                ]
            else:
                val = self._service_provider.get_role_id(self._project, val)
        elif keys[0] == "categories" and keys[1] == "value":
            if isinstance(val, list):
                val = [
                    self._service_provider.get_category_id(self._project, i)
                    for i in val
                ]
            else:
                val = self._service_provider.get_category_id(self._project, val)
        return val


class BaseCustomFieldHandler(AbstractQueryHandler):
    def __init__(
        self,
        team_id: int,
        project_id: Optional[int],
        service_provider: BaseServiceProvider,
        entity: CustomFieldEntityEnum,
        parent: CustomFieldEntityEnum,
    ):
        self._service_provider = service_provider
        self._entity = entity
        self._parent = parent
        self._team_id = team_id
        self._project_id = project_id
        self._context = {"team_id": self._team_id, "project_id": self._project_id}

    def _handle_custom_field_key(self, key) -> Tuple[str, str, Optional[str]]:
        for custom_field in sorted(
            self._service_provider.list_custom_field_names(
                self._context, self._entity, parent=self._parent
            ),
            key=len,
            reverse=True,
        ):
            if custom_field in key:
                custom_field_id = self._service_provider.get_custom_field_id(
                    self._context,
                    custom_field,
                    entity=self._entity,
                    parent=self._parent,
                )
                component_id = self._service_provider.get_custom_field_component_id(
                    self._context,
                    custom_field_id,
                    entity=self._entity,
                    parent=self._parent,
                )
                key = key.replace(
                    custom_field,
                    str(custom_field_id),
                ).split("__")
                # in case multi_select replace EQ to IN (BED requirement)
                if component_id == CustomFieldType.MULTI_SELECT.value and len(key) == 2:
                    key.append(OperatorEnum.IN.name)
                return key
        raise AppException("Invalid custom field name provided.")

    @staticmethod
    def _determine_condition_and_key(keys: List[str]) -> Tuple[OperatorEnum, str]:
        """
        Determine the condition and key from the filters.
        """
        condition: Optional[OperatorEnum] = None
        key: Optional[str] = None

        if len(keys) == 1 and "custom_field" not in keys:
            condition, key = OperatorEnum.EQ, keys[0]
        if "custom_field" in keys:
            _keys = "customField", "custom_field_values"
            if len(keys) == 2 or len(keys) == 3:
                key = ".".join((*_keys, keys[1]))
            else:
                raise AppException("Invalid custom field name provided.")
        if not condition:
            condition = (
                OperatorEnum[keys.pop().upper()]
                if keys[-1].upper() in OperatorEnum.__members__
                else OperatorEnum.EQ
            )
        if not key:
            key = ".".join(keys)
        return condition, key

    def _handle_special_fields(self, keys: List[str], val):
        if keys[0] == "custom_field":
            component_id = self._service_provider.get_custom_field_component_id(
                self._context,
                field_id=int(keys[1]),
                entity=self._entity,
                parent=self._parent,
            )
            if component_id == CustomFieldType.DATE_PICKER.value and val is not None:
                try:
                    val = val * 1000
                except Exception:
                    raise AppException("Invalid custom field value provided.")
        return val

    def handle(self, filters: Dict[str, Any], query: Query = None) -> Query:
        if query is None:
            query = EmptyQuery()
        for key, val in filters.items():
            _keys = key.split("__")
            if _keys[0] == "custom_field":
                _keys = self._handle_custom_field_key(key)
            val = self._handle_special_fields(_keys, val)
            condition, _key = self._determine_condition_and_key(_keys)
            query &= Filter(_key, val, condition)
        return super().handle(filters, query)


class UserFilterHandler(BaseCustomFieldHandler):
    def _handle_special_fields(self, keys: List[str], val):
        """
        Handle special fields like 'custom_fields__'.
        """
        if keys[0] == "role":
            try:
                if isinstance(val, list):
                    val = [UserRole.__getitem__(i.upper()).value for i in val]
                elif isinstance(val, str):
                    val = UserRole.__getitem__(val.upper()).value
                else:
                    raise AppException("Invalid user role provided.")
            except (KeyError, AttributeError):
                raise AppException("Invalid user role provided.")
        elif keys[0] == "state":
            try:
                if isinstance(val, list):
                    val = [WMUserStateEnum[i].value for i in val]
                else:
                    val = WMUserStateEnum[val].value
            except (TypeError, KeyError):
                raise AppException("Invalid user state provided.")
        return super()._handle_special_fields(keys, val)


class ProjectFilterHandler(BaseCustomFieldHandler):
    def _handle_special_fields(self, keys: List[str], val):
        """
        Handle special fields like 'status' and 'custom_fields__'.
        """
        if keys[0] == "status":
            val = (
                [ProjectStatus(i).value for i in val]
                if isinstance(val, (list, tuple, set))
                else ProjectStatus(val).value
            )
        return super()._handle_special_fields(keys, val)


class QueryBuilderChain:
    def __init__(self, handlers: List[QueryHandler]):
        if not handlers:
            raise ValueError("Handlers list cannot be empty.")

        self._head_handler = handlers[0]
        current_handler = self._head_handler

        for next_handler in handlers[1:]:
            current_handler = current_handler.set_next(next_handler)

    def handle(self, filters: Dict[str, Any], query: Query = None) -> Query:
        return self._head_handler.handle(filters, query)
