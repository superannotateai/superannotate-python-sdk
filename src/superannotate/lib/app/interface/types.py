import uuid
from functools import wraps
from pathlib import Path
from typing import Optional
from typing import Union

from lib.core.enums import AnnotationStatus
from lib.core.enums import BaseTitledEnum
from lib.core.enums import ClassTypeEnum
from lib.core.enums import ProjectStatus
from lib.core.enums import ProjectType
from lib.core.enums import UserRole
from lib.core.exceptions import AppException
from lib.infrastructure.validators import wrap_error
from pydantic import BaseModel
from pydantic import conlist
from pydantic import constr
from pydantic import errors
from pydantic import Extra
from pydantic import Field
from pydantic import parse_obj_as
from pydantic import root_validator
from pydantic import StrictStr
from pydantic import validate_arguments as pydantic_validate_arguments
from pydantic import ValidationError
from pydantic.errors import PydanticTypeError
from pydantic.errors import StrRegexError

NotEmptyStr = constr(strict=True, min_length=1)


class EnumMemberError(PydanticTypeError):
    code = "enum"

    def __str__(self) -> str:
        enum_values = list(self.enum_values)  # noqa
        if isinstance(enum_values[0], BaseTitledEnum):
            permitted = ", ".join(str(v.name) for v in enum_values)  # type: ignore
        else:
            permitted = ", ".join(f"'{str(v.value)}'" for v in enum_values)  # type: ignore
        return f"Available values are: {permitted}"


errors.EnumMemberError = EnumMemberError


class EmailStr(StrictStr):
    @classmethod
    def validate(cls, value: Union[str]) -> Union[str]:
        try:
            constr(
                regex=r"^(?=.{1,254}$)(?=.{1,64}@)[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+)"
                r"*@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}"
                r"[a-zA-Z0-9])?)*$"
            ).validate(value)
        except StrRegexError:
            raise ValueError("Invalid email")
        return value


class ProjectStatusEnum(StrictStr):
    @classmethod
    def validate(cls, value: Union[str]) -> Union[str]:
        if cls.curtail_length and len(value) > cls.curtail_length:
            value = value[: cls.curtail_length]
        if value.lower() not in ProjectStatus.values():
            raise TypeError(
                f"Available statuses is {', '.join(ProjectStatus.titles())}. "
            )
        return value


class AnnotatorRole(StrictStr):
    ANNOTATOR_ROLES = (UserRole.ADMIN.name, UserRole.ANNOTATOR.name, UserRole.QA.name)

    @classmethod
    def validate(cls, value: Union[str]) -> Union[str]:
        if cls.curtail_length and len(value) > cls.curtail_length:
            value = value[: cls.curtail_length]
        if value.lower() not in [role.lower() for role in cls.ANNOTATOR_ROLES]:
            raise TypeError(
                f"Invalid user role provided. Please specify one of {', '.join(cls.ANNOTATOR_ROLES)}. "
            )
        return value


class AnnotationType(StrictStr):
    VALID_TYPES = ["bbox", "polygon", "point"]

    @classmethod
    def validate(cls, value: Union[str]) -> Union[str]:
        if value.lower() not in cls.VALID_TYPES:
            raise TypeError(
                f"Available annotation_types are {', '.join(cls.VALID_TYPES)}. "
            )
        return value


class AttachmentDict(BaseModel):
    url: StrictStr
    name: Optional[StrictStr] = Field(default_factory=lambda: str(uuid.uuid4()))

    class Config:
        extra = Extra.ignore

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return self.url == other.url and self.name.strip() == other.name.strip()


AttachmentArgType = Union[NotEmptyStr, Path, conlist(AttachmentDict, min_items=1)]


class Setting(BaseModel):
    attribute: NotEmptyStr
    value: Union[NotEmptyStr, float, int]

    class Config:
        extra = Extra.ignore


class AttachmentArg(BaseModel):
    __root__: AttachmentArgType

    def __getitem__(self, index):
        return self.__root__[index]

    @property
    def data(self):
        return self.__root__

    @root_validator(pre=True)
    def validate_root(cls, values):
        try:
            parse_obj_as(AttachmentArgType, values["__root__"])
        except ValidationError:
            raise ValueError(
                "The value must be str, path, or list of dicts with the required 'url' and optional 'name' keys"
            )
        return values


class ImageQualityChoices(StrictStr):
    VALID_CHOICES = ["compressed", "original"]

    @classmethod
    def validate(cls, value: Union[str]) -> Union[str]:
        super().validate(value)
        if value.lower() not in cls.VALID_CHOICES:
            raise TypeError(
                f"Image quality available choices are {', '.join(cls.VALID_CHOICES)}."
            )
        return value.lower()


class ProjectTypes(StrictStr):
    @classmethod
    def validate(cls, value: Union[str]) -> Union[str]:
        if value.lower() not in ProjectType.values():
            raise TypeError(
                f" Available project types are {', '.join(ProjectType.titles())}. "
            )
        return value


class ClassType(StrictStr):
    @classmethod
    def validate(cls, value: Union[str]) -> Union[str]:
        enum_values = [e.name.lower() for e in ClassTypeEnum]
        if value.lower() not in enum_values:
            raise TypeError(
                f"Invalid type provided. Please specify one of the {', '.join(enum_values)}. "
            )
        return value.lower()


class AnnotationStatuses(StrictStr):
    @classmethod
    def validate(cls, value: Union[str]) -> Union[str]:
        if value.lower() not in AnnotationStatus.values():
            raise TypeError(
                f"Available an notation_statuses are {', '.join(AnnotationStatus.titles())}. "
            )
        return value


def validate_arguments(func):
    @wraps(func)
    def wrapped(self, *args, **kwargs):
        try:
            return pydantic_validate_arguments(func)(self, *args, **kwargs)
        except ValidationError as e:
            raise AppException(wrap_error(e))

    return wrapped
