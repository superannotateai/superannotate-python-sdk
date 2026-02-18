"""
Pydantic v2 compatibility layer.
This module provides a unified interface for Pydantic v2.
"""
from datetime import datetime
from typing import Any
from typing import Callable
from typing import get_args
from typing import Literal
from typing import Sequence
from typing import Type
from typing import TypeVar
from typing import Union

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator
from pydantic import RootModel
from pydantic import StrictBool
from pydantic import StrictFloat
from pydantic import StrictInt
from pydantic import StrictStr
from pydantic import TypeAdapter
from pydantic import validate_call
from pydantic import ValidationError
from pydantic.functional_validators import BeforeValidator
from pydantic_extra_types.color import Color

# Re-export for compatibility
Literal = Literal
BaseModel = BaseModel
Field = Field
ValidationError = ValidationError
StrictStr = StrictStr
StrictInt = StrictInt
StrictBool = StrictBool
StrictFloat = StrictFloat
Color = Color
ColorType = Union[Color, str, tuple]


# Compatibility shim for Extra enum
class Extra:
    allow = "allow"
    ignore = "ignore"
    forbid = "forbid"


# Compatibility shim for constr
def constr(
    *,
    strict: bool = False,
    min_length: int = None,
    max_length: int = None,
    pattern: str = None,
    regex: str = None,  # v1 compatibility
) -> Type[str]:
    """Constrained string type compatible with v1 API."""
    from pydantic import constr as pydantic_constr

    # v1 used 'regex', v2 uses 'pattern'
    actual_pattern = pattern or regex
    return pydantic_constr(
        strict=strict,
        min_length=min_length,
        max_length=max_length,
        pattern=actual_pattern,
    )


# Compatibility shim for conlist
def conlist(
    item_type: Type,
    *,
    min_length: int = None,
    max_length: int = None,
    min_items: int = None,  # v1 compatibility
    max_items: int = None,  # v1 compatibility
) -> Type[list]:
    """Constrained list type compatible with v1 API."""
    from pydantic import conlist as pydantic_conlist

    # v1 used min_items/max_items, v2 uses min_length/max_length
    actual_min = min_length if min_length is not None else min_items
    actual_max = max_length if max_length is not None else max_items
    return pydantic_conlist(item_type, min_length=actual_min, max_length=actual_max)


# Compatibility shim for parse_obj_as
T = TypeVar("T")


def parse_obj_as(type_: Type[T], obj: Any) -> T:
    """Parse an object as a given type using TypeAdapter."""
    adapter = TypeAdapter(type_)
    return adapter.validate_python(obj)


# Compatibility shim for parse_datetime
def parse_datetime(value: Any) -> datetime:
    """Parse a datetime value."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        from dateutil.parser import parse

        return parse(value)
    raise ValueError(f"Cannot parse datetime from {type(value)}")


# Compatibility shim for is_namedtuple
def is_namedtuple(type_: Type) -> bool:
    """Check if a type is a namedtuple."""
    return (
        isinstance(type_, type)
        and issubclass(type_, tuple)
        and hasattr(type_, "_fields")
    )


# Compatibility shim for sequence_like
def sequence_like(v: Any) -> bool:
    """Check if a value is sequence-like."""
    return isinstance(v, (list, tuple, set, frozenset, Sequence)) and not isinstance(
        v, (str, bytes)
    )


# Compatibility for ROOT_KEY
ROOT_KEY = "__root__"


# Compatibility for ValueItems - simplified implementation
class ValueItems:
    """Simplified ValueItems for v2 compatibility."""

    __slots__ = ("_items", "_type")

    def __init__(self, value: Any, items: Any) -> None:
        self._items = items
        self._type = type(value)

    def is_excluded(self, item: Any) -> bool:
        return item in self._items if self._items else False

    def is_included(self, item: Any) -> bool:
        return item in self._items if self._items else True


# Compatibility shim for validator decorator (maps to field_validator)
def validator(*fields: str, pre: bool = False, always: bool = False, **kwargs):
    """Compatibility wrapper for v1 validator decorator."""
    mode = "before" if pre else "after"

    def decorator(func: Callable) -> Callable:
        # Wrap the function to handle v1-style signature
        return field_validator(*fields, mode=mode, **kwargs)(classmethod(func))

    return decorator


# Compatibility shim for root_validator decorator (maps to model_validator)
def root_validator(*, pre: bool = False, **kwargs):
    """Compatibility wrapper for v1 root_validator decorator."""
    mode = "before" if pre else "after"

    def decorator(func: Callable) -> Callable:
        return model_validator(mode=mode)(classmethod(func))

    return decorator


# Compatibility shim for validate_arguments (maps to validate_call)
pydantic_validate_arguments = validate_call


# Compatibility shim for error types
class PydanticTypeError(Exception):
    """Base class for Pydantic type errors."""

    code = "type_error"
    msg_template = "Invalid type"

    def __init__(self, **ctx):
        self.__dict__.update(ctx)

    def __str__(self):
        return self.msg_template.format(**self.__dict__)


class WrongConstantError(PydanticTypeError):
    """Error for wrong constant values."""

    code = "const"
    msg_template = "unexpected value; permitted: {permitted}"

    def __init__(self, *, given: Any, permitted: Sequence):
        super().__init__(given=given, permitted=permitted)


class StrRegexError(PydanticTypeError):
    """Error for string regex validation failures."""

    code = "str.regex"
    msg_template = "string does not match regex '{pattern}'"


# Compatibility shim for ErrorWrapper
class ErrorWrapper:
    """Compatibility wrapper for v1 ErrorWrapper."""

    def __init__(self, exc: Exception, loc: tuple):
        self.exc = exc
        self.loc = loc


# Compatibility module for errors
class errors:
    """Namespace for error types."""

    PydanticTypeError = PydanticTypeError
    WrongConstantError = WrongConstantError
    StrRegexError = StrRegexError
    EnumMemberError = None  # Will be set by types.py


# Compatibility module for validators
class validators:
    """Namespace for validator utilities."""

    @staticmethod
    def all_literal_values(type_: Type) -> tuple:
        """Get all literal values from a Literal type."""
        return get_args(type_)

    # These will be set by validators.py
    make_literal_validator = None
    make_typeddict_validator = None


# Compatibility shim for create_model_from_typeddict
def create_model_from_typeddict(
    typeddict_cls: Type, *, __config__: Type = None, __module__: str = None
) -> Type[BaseModel]:
    """Create a Pydantic model from a TypedDict."""
    from pydantic import create_model

    annotations = getattr(typeddict_cls, "__annotations__", {})
    fields = {name: (typ, ...) for name, typ in annotations.items()}

    config = None
    if __config__:
        # Convert v1 Config class to v2 ConfigDict
        config_dict = {}
        if hasattr(__config__, "extra"):
            extra_val = __config__.extra
            if hasattr(extra_val, "value"):
                config_dict["extra"] = extra_val.value
            else:
                config_dict["extra"] = extra_val
        config = ConfigDict(**config_dict) if config_dict else None

    model = create_model(
        typeddict_cls.__name__,
        __module__=__module__ or typeddict_cls.__module__,
        **fields,
    )

    if config:
        model.model_config = config

    return model
