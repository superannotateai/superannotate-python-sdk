import uuid
from datetime import datetime
from enum import Enum
from typing import Any
from typing import List
from typing import Optional
from typing import Union
from typing import no_type_check

from pydantic import BaseModel as PydanticBaseModel
from pydantic import Extra
from pydantic import Field
from pydantic.datetime_parse import parse_datetime
from pydantic.typing import is_namedtuple
from pydantic.utils import ROOT_KEY
from pydantic.utils import ValueItems
from pydantic.utils import sequence_like

from lib.core.enums import AnnotationStatus
from lib.core.enums import BaseTitledEnum

try:
    from pydantic import AbstractSetIntStr  # noqa
    from pydantic import MappingIntStrAny  # noqa
except ImportError:
    pass


class BaseModel(PydanticBaseModel):
    """

    """
    @classmethod
    @no_type_check
    def _get_value(
            cls,
            v: Any,
            to_dict: bool,
            by_alias: bool,
            include: Optional[Union['AbstractSetIntStr', 'MappingIntStrAny']],
            exclude: Optional[Union['AbstractSetIntStr', 'MappingIntStrAny']],
            exclude_unset: bool,
            exclude_defaults: bool,
            exclude_none: bool,
    ) -> Any:

        if isinstance(v, BaseModel):
            if to_dict:
                v_dict = v.dict(
                    by_alias=by_alias,
                    exclude_unset=exclude_unset,
                    exclude_defaults=exclude_defaults,
                    include=include,
                    exclude=exclude,
                    exclude_none=exclude_none,
                )
                if ROOT_KEY in v_dict:
                    return v_dict[ROOT_KEY]
                return v_dict
            else:
                return v.copy(include=include, exclude=exclude)

        value_exclude = ValueItems(v, exclude) if exclude else None
        value_include = ValueItems(v, include) if include else None

        if isinstance(v, dict):
            return {
                k_: cls._get_value(
                    v_,
                    to_dict=to_dict,
                    by_alias=by_alias,
                    exclude_unset=exclude_unset,
                    exclude_defaults=exclude_defaults,
                    include=value_include and value_include.for_element(k_),
                    exclude=value_exclude and value_exclude.for_element(k_),
                    exclude_none=exclude_none,
                )
                for k_, v_ in v.items()
                if (not value_exclude or not value_exclude.is_excluded(k_))
                   and (not value_include or value_include.is_included(k_))
            }

        elif sequence_like(v):
            seq_args = (
                cls._get_value(
                    v_,
                    to_dict=to_dict,
                    by_alias=by_alias,
                    exclude_unset=exclude_unset,
                    exclude_defaults=exclude_defaults,
                    include=value_include and value_include.for_element(i),
                    exclude=value_exclude and value_exclude.for_element(i),
                    exclude_none=exclude_none,
                )
                for i, v_ in enumerate(v)
                if (not value_exclude or not value_exclude.is_excluded(i))
                   and (not value_include or value_include.is_included(i))
            )

            return v.__class__(*seq_args) if is_namedtuple(v.__class__) else v.__class__(seq_args)
        elif isinstance(v, BaseTitledEnum) and getattr(cls.Config, 'use_enum_names', False):
            return v.name
        elif isinstance(v, Enum) and getattr(cls.Config, 'use_enum_values', False):
            return v.name
        else:
            return v


class StringDate(datetime):
    @classmethod
    def __get_validators__(cls):
        yield parse_datetime
        yield cls.validate

    @classmethod
    def validate(cls, v: datetime):
        return v.isoformat()


class SubSetEntity(BaseModel):
    id: Optional[int]
    name: str

    class Config:
        extra = Extra.ignore


class TimedBaseModel(BaseModel):
    createdAt: StringDate = Field(None, alias="createdAt")
    updatedAt: StringDate = Field(None, alias="updatedAt")


class BaseItemEntity(TimedBaseModel):
    name: str
    path: Optional[str] = Field(
        None, description="Item’s path in SuperAnnotate project"
    )
    url: Optional[str] = Field(description="Publicly available HTTP address")
    annotator_email: Optional[str] = Field(description="Annotator email")
    qa_email: Optional[str] = Field(description="QA email")
    annotation_status: AnnotationStatus = Field(description="Item annotation status")
    entropy_value: Optional[float] = Field(description="Priority score of given item")
    createdAt: str = Field(description="Date of creation")
    updatedAt: str = Field(description="Update date")
    custom_metadata: Optional[dict]

    class Config:
        extra = Extra.allow

    def add_path(self, project_name: str, folder_name: str):
        self.path = (
            f"{project_name}{f'/{folder_name}' if folder_name != 'root' else ''}"
        )
        return self

    @staticmethod
    def map_fields(entity: dict) -> dict:
        entity["url"] = entity.get("path")
        entity["path"] = None
        entity["annotator_email"] = entity.get("annotator_id")
        entity["qa_email"] = entity.get("qa_id")
        return entity
