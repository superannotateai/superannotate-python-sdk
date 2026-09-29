import re
from datetime import datetime
from datetime import timedelta
from functools import wraps
from typing import Annotated

from lib.core.exceptions import AppException
from lib.infrastructure.validators import wrap_error
from pydantic import AfterValidator
from pydantic import Strict
from pydantic import StrictInt
from pydantic import validate_call as pydantic_validate_arguments
from pydantic import ValidationError

EMAIL_PATTERN = re.compile(
    r"^(?=.{1,254}$)(?=.{1,64}@)[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+"
    r"(?:\.[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+)*"
    r"@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
)


def _validate_email(value: str) -> str:
    """Validate email format."""
    if not EMAIL_PATTERN.match(value):
        raise ValueError("Invalid email")
    return value


EmailStr = Annotated[str, AfterValidator(_validate_email)]

#: When something expires: a number of days from now, a duration, or the date itself.
#: Every member is strict on purpose - left lax, ``30.5`` is no valid number of days,
#: so it would be read as 30.5 *seconds* through timedelta and silently expire in half
#: a minute.
ExpiresIn = StrictInt | Annotated[timedelta, Strict()] | Annotated[datetime, Strict()]


def validate_arguments(func):
    @wraps(func)
    def wrapped(self, *args, **kwargs):
        try:
            return pydantic_validate_arguments(func)(self, *args, **kwargs)
        except ValidationError as e:
            raise AppException(wrap_error(e)) from e

    return wrapped
