import re
from functools import wraps
from typing import Annotated
from typing import Union

from pydantic import AfterValidator
from pydantic import StrictStr
from pydantic import validate_call
from pydantic import ValidationError

from lib.core.enums import BaseTitledEnum
from lib.core.exceptions import AppException
from lib.core.pydantic_v1 import errors
from lib.core.pydantic_v1 import PydanticTypeError
from lib.infrastructure.validators import wrap_error


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


# Email validation pattern
_EMAIL_PATTERN = re.compile(
    r"^(?=.{1,254}$)(?=.{1,64}@)[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+)"
    r"*@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}"
    r"[a-zA-Z0-9])?)*$"
)


def _validate_email(value: str) -> str:
    """Validate email format."""
    if not _EMAIL_PATTERN.match(value):
        raise ValueError("Invalid email")
    return value


EmailStr = Annotated[StrictStr, AfterValidator(_validate_email)]


def validate_arguments(func):
    validated_func = validate_call(func)

    @wraps(func)
    def wrapped(self, *args, **kwargs):
        try:
            return validated_func(self, *args, **kwargs)
        except ValidationError as e:
            raise AppException(wrap_error(e)) from e

    return wrapped
