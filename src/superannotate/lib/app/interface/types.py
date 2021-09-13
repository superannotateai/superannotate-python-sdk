from functools import wraps
from typing import List
from typing import Optional
from typing import Union

from lib.core.enums import AnnotationStatus
from pydantic import BaseModel
from pydantic import constr
from pydantic import StrictStr
from pydantic import validate_arguments as pydantic_validate_arguments
from pydantic import ValidationError


NotEmptyStr = constr(strict=True, min_length=1)


class Status(StrictStr):
    @classmethod
    def validate(cls, value: Union[str]) -> Union[str]:
        if cls.curtail_length and len(value) > cls.curtail_length:
            value = value[: cls.curtail_length]
        if value.lower() not in AnnotationStatus.values():
            raise TypeError(f"Available statuses is {', '.join(AnnotationStatus)}. ")
        return value


class AttributeGroup(BaseModel):
    name: StrictStr
    is_multiselect: Optional[bool]


class ClassesJson(BaseModel):
    name: StrictStr
    color: StrictStr
    attribute_groups: List[AttributeGroup]


def validate_arguments(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return pydantic_validate_arguments(func)(*args, **kwargs)
        except ValidationError as e:
            raise e

    return wrapped
