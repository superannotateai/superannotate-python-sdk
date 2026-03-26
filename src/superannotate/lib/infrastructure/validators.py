import os
import typing
from collections import defaultdict
from typing import get_args
from typing import get_origin

from pydantic import ValidationError


class WrongConstantError(ValueError):
    """Custom error for wrong constant values."""

    def __init__(self, given: typing.Any, permitted: typing.Tuple[typing.Any, ...]):
        self.given = given
        self.permitted = permitted
        super().__init__(self._message())

    def _message(self) -> str:
        permitted = ", ".join(repr(v) for v in self.permitted)
        return f"Available values are {permitted}."

    def __str__(self) -> str:
        return self._message()


def all_literal_values(type_: typing.Any) -> typing.Tuple[typing.Any, ...]:
    """Extract all literal values from a Literal type."""
    origin = get_origin(type_)
    if origin is typing.Literal:
        return get_args(type_)
    # Handle Union of Literals
    if origin is typing.Union:
        values = []
        for arg in get_args(type_):
            if get_origin(arg) is typing.Literal:
                values.extend(get_args(arg))
        return tuple(values)
    return ()


def make_literal_validator(
    type_: typing.Any,
) -> typing.Callable[[typing.Any], typing.Any]:
    """
    Adding ability to input literal in the lower case.
    """
    permitted_choices = all_literal_values(type_)
    allowed_choices = {
        v.lower() if isinstance(v, str) and v else v: v for v in permitted_choices
    }

    def literal_validator(v: typing.Any) -> typing.Any:
        try:
            return allowed_choices[v.lower() if isinstance(v, str) else v]
        except (KeyError, AttributeError):
            raise WrongConstantError(given=v, permitted=permitted_choices)

    return literal_validator


def get_tabulation() -> int:
    try:
        return int(os.get_terminal_size().columns / 2)
    except OSError:
        return 48


def _is_pydantic_internal_loc(loc_part: typing.Any) -> bool:
    """
    Check if a location part is a Pydantic v2 internal type descriptor.
    These are not human-readable and should be filtered out.
    Examples of internal descriptors:
    - 'constrained-str'
    - 'lax-or-strict[...]'
    - 'list[SomeModel]'
    - 'json-or-python[...]'
    - 'function-after[...]'
    - 'union[...]'
    """
    if not isinstance(loc_part, str):
        return False
    # These patterns indicate internal Pydantic type descriptors
    internal_patterns = (
        "constrained-",
        "lax-or-strict[",
        "json-or-python[",
        "function-after[",
        "function-before[",
        "function-wrap[",
        "union[",
        "is-instance[",
    )
    if loc_part.startswith(internal_patterns):
        return True
    # Also filter out patterns like 'list[Model]' or 'dict[str, Model]'
    # but keep simple field names
    if "[" in loc_part and "]" in loc_part:
        # Check if it looks like a type descriptor (e.g., 'list[Attachment]')
        # rather than a field name
        return True
    return False


def wrap_error(e: ValidationError) -> str:
    tabulation = get_tabulation()
    error_messages = defaultdict(list)
    for error in e.errors():
        error_loc = list(error["loc"])
        # Filter out Pydantic v2 internal type descriptors
        error_loc = [loc for loc in error_loc if not _is_pydantic_internal_loc(loc)]
        if len(error_loc) == 0:
            continue
        if len(error_loc) == 1 and isinstance(error_loc[0], int):
            errors_list = [f"argument at index {error_loc[0]}"]
        else:
            errors_list = list(error_loc)
        if "__root__" in errors_list:
            errors_list.remove("__root__")
        errors_list[1::] = [
            f"[{i}]" if isinstance(i, int) else f".{i}" for i in errors_list[1::]
        ]
        error_messages["".join([str(item) for item in errors_list])].append(
            error["msg"]
        )
    texts = ["\n"]
    for field, text in error_messages.items():
        texts.append(
            "{} {}{}".format(
                field,
                " " * (tabulation - len(field)),
                f"\n {' ' * tabulation}".join(text),
            )
        )
    return "\n".join(texts)
