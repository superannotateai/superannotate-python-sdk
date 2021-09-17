from collections import defaultdict
from functools import wraps
from typing import Union

from lib.core.enums import AnnotationStatus
from lib.core.exceptions import AppException
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


class AnnotationType(StrictStr):
    VALID_TYPES = ["bbox", "polygon", "point"]

    @classmethod
    def validate(cls, value: Union[str]) -> Union[str]:
        if value.lower() not in cls.VALID_TYPES:
            raise TypeError(
                f"Available annotation_types are {', '.join(cls.VALID_TYPES)}. "
            )
        return value


def validate_arguments(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return pydantic_validate_arguments(func)(*args, **kwargs)
        except ValidationError as e:
            error_messages = defaultdict(list)
            for error in e.errors():
                error_messages[error["loc"][0]].append(
                    f"{error['loc'][-1]} {error['msg']}"
                )
            texts = ["\n"]
            for error, text in error_messages.items():
                texts.append(
                    "{} |{}{}".format(
                        error, " " * (20 - len(error) + 1), f"\n {' ' * 20}".join(text)
                    )
                )
            raise AppException("\n".join(texts))

    return wrapped
