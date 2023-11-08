import re
import warnings
from datetime import datetime
from enum import Enum
from typing import Any
from typing import Callable
from typing import cast
from typing import no_type_check
from typing import Optional
from typing import Union

from lib.core import BACKEND_URL
from lib.core import LOG_FILE_LOCATION
from lib.core.enums import AnnotationStatus
from lib.core.enums import BaseTitledEnum
from lib.core.pydantic_v1 import BaseModel
from lib.core.pydantic_v1 import Extra
from lib.core.pydantic_v1 import Field
from lib.core.pydantic_v1 import is_namedtuple
from lib.core.pydantic_v1 import Literal
from lib.core.pydantic_v1 import parse_datetime
from lib.core.pydantic_v1 import ROOT_KEY
from lib.core.pydantic_v1 import sequence_like
from lib.core.pydantic_v1 import StrictStr
from lib.core.pydantic_v1 import ValueItems

DATE_TIME_FORMAT_ERROR_MESSAGE = (
    "does not match expected format YYYY-MM-DDTHH:MM:SS.fffZ"
)
DATE_REGEX = r"\d{4}-[01]\d-[0-3]\dT[0-2]\d:[0-5]\d:[0-5]\d(?:\.\d{3})Z"

try:
    from pydantic import AbstractSetIntStr  # noqa
    from pydantic import MappingIntStrAny  # noqa
except ImportError:
    pass
_missing = object()


class BaseModel(BaseModel):
    """
    Added new extra keys
    - use_enum_names: that's for BaseTitledEnum to use names instead of enum objects
    """

    def _iter(
        self,
        to_dict: bool = False,
        by_alias: bool = False,
        include: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        exclude: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ) -> "TupleGenerator":  # noqa

        # Merge field set excludes with explicit exclude parameter with explicit overriding field set options.
        # The extra "is not None" guards are not logically necessary but optimizes performance for the simple case.
        if exclude is not None or self.__exclude_fields__ is not None:
            exclude = ValueItems.merge(self.__exclude_fields__, exclude)

        if include is not None or self.__include_fields__ is not None:
            include = ValueItems.merge(self.__include_fields__, include, intersect=True)

        allowed_keys = self._calculate_keys(
            include=include, exclude=exclude, exclude_unset=exclude_unset  # type: ignore
        )
        if allowed_keys is None and not (
            by_alias or exclude_unset or exclude_defaults or exclude_none
        ):
            # huge boost for plain _iter()
            yield from self.__dict__.items()
            return

        value_exclude = ValueItems(self, exclude) if exclude is not None else None
        value_include = ValueItems(self, include) if include is not None else None

        for field_key, v in self.__dict__.items():
            if (allowed_keys is not None and field_key not in allowed_keys) or (
                exclude_none and v is None
            ):
                continue

            if exclude_defaults:
                model_field = self.__fields__.get(field_key)
                if (
                    not getattr(model_field, "required", True)
                    and getattr(model_field, "default", _missing) == v
                ):
                    continue

            if by_alias and field_key in self.__fields__:
                dict_key = self.__fields__[field_key].alias
            else:
                dict_key = field_key

            # if to_dict or value_include or value_exclude:
            v = self._get_value(
                v,
                to_dict=to_dict,
                by_alias=by_alias,
                include=value_include and value_include.for_element(field_key),
                exclude=value_exclude and value_exclude.for_element(field_key),
                exclude_unset=exclude_unset,
                exclude_defaults=exclude_defaults,
                exclude_none=exclude_none,
            )
            yield dict_key, v

    @classmethod
    @no_type_check
    def _get_value(
        cls,
        v: Any,
        to_dict: bool,
        by_alias: bool,
        include: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]],
        exclude: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]],
        exclude_unset: bool,
        exclude_defaults: bool,
        exclude_none: bool,
    ) -> Any:

        if isinstance(v, BaseModel):
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

            return (
                v.__class__(*seq_args)
                if is_namedtuple(v.__class__)
                else v.__class__(seq_args)
            )
        elif (
            isinstance(v, BaseTitledEnum)
            and getattr(cls.Config, "use_enum_names", False)
            and to_dict
        ):
            return v.name
        elif isinstance(v, Enum) and getattr(cls.Config, "use_enum_values", False):
            return v.name
        else:
            return v

    def json(
        self,
        *,
        include: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        exclude: Optional[Union["AbstractSetIntStr", "MappingIntStrAny"]] = None,
        by_alias: bool = False,
        skip_defaults: Optional[bool] = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        encoder: Optional[Callable[[Any], Any]] = None,
        models_as_dict: bool = True,
        **dumps_kwargs: Any,
    ) -> str:
        """
        Generate a JSON representation of the model, `include` and `exclude` arguments as per `dict()`.

        `encoder` is an optional function to supply as `default` to json.dumps(), other arguments as per `json.dumps()`.
        """
        if skip_defaults is not None:
            warnings.warn(
                f'{self.__class__.__name__}.json(): "skip_defaults" is deprecated and replaced by "exclude_unset"',
                DeprecationWarning,
            )
            exclude_unset = skip_defaults
        encoder = cast(Callable[[Any], Any], encoder or self.__json_encoder__)

        # We don't directly call `self.dict()`, which does exactly this with `to_dict=True`
        # because we want to be able to keep raw `BaseModel` instances and not as `dict`.
        # This allows users to write custom JSON encoders for given `BaseModel` classes.
        data = dict(
            self._iter(
                to_dict=False,
                by_alias=by_alias,
                include=include,
                exclude=exclude,
                exclude_unset=exclude_unset,
                exclude_defaults=exclude_defaults,
                exclude_none=exclude_none,
            )
        )
        if self.__custom_root_type__:
            data = data[ROOT_KEY]
        return self.__config__.json_dumps(data, default=encoder, **dumps_kwargs)


class StringDate(datetime):
    @classmethod
    def __get_validators__(cls):
        yield parse_datetime
        yield cls.validate

    @classmethod
    def validate(cls, v: datetime):
        v = v.isoformat().split("+")[0] + ".000Z"
        return v


class SubSetEntity(BaseModel):
    id: Optional[int]
    name: str

    class Config:
        extra = Extra.ignore


class TimedBaseModel(BaseModel):
    createdAt: Optional[StringDate] = Field(
        None, alias="createdAt", description="Date of creation"
    )
    updatedAt: Optional[StringDate] = Field(
        None, alias="updatedAt", description="Update date"
    )


class BaseItemEntity(TimedBaseModel):
    id: Optional[int]
    name: Optional[str]
    path: Optional[str] = Field(
        None, description="Item’s path in SuperAnnotate project"
    )
    url: Optional[str] = Field(description="Publicly available HTTP address")
    annotator_email: Optional[str] = Field(description="Annotator email")
    qa_email: Optional[str] = Field(description="QA email")
    annotation_status: Optional[AnnotationStatus] = Field(
        None, description="Item annotation status"
    )
    entropy_value: Optional[float] = Field(description="Priority score of given item")
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


class TokenStr(StrictStr):
    regex = r"^[-.@_A-Za-z0-9]+=\d+$"

    @classmethod
    def validate(cls, value: Union[str]) -> Union[str]:
        if cls.curtail_length and len(value) > cls.curtail_length:
            value = value[: cls.curtail_length]
        if cls.regex:
            if not re.match(cls.regex, value):
                raise ValueError("Invalid token.")
        return value


class ConfigEntity(BaseModel):
    API_TOKEN: TokenStr = Field(alias="SA_TOKEN")
    API_URL: str = Field(alias="SA_URL", default=BACKEND_URL)
    LOGGING_LEVEL: Literal[
        "NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
    ] = "INFO"
    LOGGING_PATH: str = f"{LOG_FILE_LOCATION}"
    VERIFY_SSL: bool = True
    ANNOTATION_CHUNK_SIZE = 5000
    ITEM_CHUNK_SIZE = 2000
    MAX_THREAD_COUNT = 4
    MAX_COROUTINE_COUNT = 8

    class Config:
        extra = Extra.ignore
