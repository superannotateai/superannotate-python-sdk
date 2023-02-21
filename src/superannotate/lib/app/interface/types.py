from functools import wraps
from typing import Union

from lib.core.enums import BaseTitledEnum
from lib.core.exceptions import AppException
from lib.infrastructure.validators import wrap_error
from pydantic import constr
from pydantic import errors
from pydantic import StrictStr
from pydantic import validate_arguments as pydantic_validate_arguments
from pydantic import ValidationError
from pydantic.errors import PydanticTypeError
from pydantic.errors import StrRegexError


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
            ).validate(  # noqa
                value
            )
        except StrRegexError:
            raise ValueError("Invalid email")
        return value


def validate_arguments(func):
    @wraps(func)
    def wrapped(self, *args, **kwargs):
        try:
            return pydantic_validate_arguments(func)(self, *args, **kwargs)
        except ValidationError as e:
            raise AppException(wrap_error(e)) from e

    return wrapped
