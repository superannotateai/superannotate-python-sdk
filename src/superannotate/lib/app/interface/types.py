from functools import wraps
from typing import Union

from lib.core.enums import AnnotationStatus
from lib.core.enums import ClassTypeEnum
from lib.core.enums import ProjectStatus
from lib.core.enums import ProjectType
from lib.core.enums import UserRole
from lib.core.exceptions import AppException
from lib.infrastructure.validators import wrap_error
from pydantic import constr
from pydantic import StrictStr
from pydantic import validate_arguments as pydantic_validate_arguments
from pydantic import ValidationError
from pydantic.errors import StrRegexError

NotEmptyStr = constr(strict=True, min_length=1)


class EmailStr(StrictStr):
    @classmethod
    def validate(cls, value: Union[str]) -> Union[str]:
        try:
            constr(
                regex=r"^(?=.{1,254}$)(?=.{1,64}@)[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+)*@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
            ).validate(value)
        except StrRegexError:
            raise ValueError("Invalid email")
        return value


class Status(StrictStr):
    @classmethod
    def validate(cls, value: Union[str]) -> Union[str]:
        if cls.curtail_length and len(value) > cls.curtail_length:
            value = value[: cls.curtail_length]
        if value.lower() not in AnnotationStatus.values():
            raise TypeError(
                f"Available statuses is {', '.join(AnnotationStatus.titles())}. "
            )
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
                f"Available annotation_statuses are {', '.join(AnnotationStatus.titles())}. "
            )
        return value


def validate_arguments(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return pydantic_validate_arguments(func)(*args, **kwargs)
        except ValidationError as e:
            raise AppException(wrap_error(e))

    return wrapped
