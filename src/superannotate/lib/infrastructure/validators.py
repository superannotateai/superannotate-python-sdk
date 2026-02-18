import os
import typing
from collections import defaultdict
from typing import get_args

from pydantic import ValidationError

from lib.core.pydantic_v1 import WrongConstantError


def wrong_constant_error(self):
    permitted = ", ".join(repr(v) for v in self.permitted)  # type: ignore
    return f"Available values are {permitted}."


WrongConstantError.__str__ = wrong_constant_error


def all_literal_values(type_: typing.Any) -> tuple:
    """Get all literal values from a Literal type."""
    return get_args(type_)


def make_literal_validator(
    type_: typing.Any,
) -> typing.Callable[[typing.Any], typing.Any]:
    """
    Adding ability to input literal in the lower case.
    """
    permitted_choices = all_literal_values(type_)
    allowed_choices = {v.lower() if v else v: v for v in permitted_choices}

    def literal_validator(v: typing.Any) -> typing.Any:
        try:
            return allowed_choices[v.lower()]
        except (KeyError, AttributeError):
            raise WrongConstantError(given=v, permitted=permitted_choices)

    return literal_validator


def make_typeddict_validator(
    typeddict_cls: typing.Type["TypedDict"], config: typing.Type["BaseConfig"]  # type: ignore[valid-type]
) -> typing.Callable[[typing.Any], typing.Dict[str, typing.Any]]:
    """
    Wrapping to ignore extra keys
    """
    from pydantic import ConfigDict
    from pydantic import create_model

    annotations = getattr(typeddict_cls, "__annotations__", {})
    fields = {name: (typ, ...) for name, typ in annotations.items()}

    TypedDictModel = create_model(
        typeddict_cls.__name__,
        __module__=typeddict_cls.__module__,
        **fields,
    )
    TypedDictModel.model_config = ConfigDict(extra="ignore")
    typeddict_cls.__pydantic_model__ = TypedDictModel  # type: ignore[attr-defined]

    def typeddict_validator(values: "TypedDict") -> typing.Dict[str, typing.Any]:  # type: ignore[valid-type]
        return TypedDictModel.model_validate(values).model_dump(exclude_unset=True)

    return typeddict_validator


# Register validators in the compatibility module
from lib.core.pydantic_v1 import validators

validators.make_literal_validator = make_literal_validator
validators.make_typeddict_validator = make_typeddict_validator
validators.all_literal_values = all_literal_values


def get_tabulation() -> int:
    try:
        return int(os.get_terminal_size().columns / 2)
    except OSError:
        return 48


def _extract_field_from_type_loc(item_str: str) -> str:
    """Extract field name from Pydantic v2 type location strings.

    Examples:
    - 'list[Attachment][0]' -> extracts index [0]
    - 'str' -> returns None (skip)
    - 'constrained-str' -> returns None (skip)
    """
    import re

    # Skip simple type names
    skip_types = {"str", "int", "float", "bool", "constrained-str"}
    if item_str in skip_types:
        return None

    # Extract list indices like 'list[Attachment][0]' -> '[0]'
    match = re.search(r"\](\[\d+\])$", item_str)
    if match:
        return match.group(1)

    return None


def _clean_loc_item(item, is_first: bool = False) -> tuple:
    """Clean up Pydantic v2 location items.

    Pydantic v2 includes type information in locations like:
    - 'function-wrap[validate_arguments()]'
    - '2.constrained-str'
    - '2.lax-or-strict[...]'
    - '2.list[Attachment][0]'

    Returns a tuple of (cleaned_value, is_index) where is_index indicates
    if the value should be formatted as an index [n].
    """
    if isinstance(item, int):
        return (str(item), True)

    item_str = str(item)

    # Skip internal Pydantic v2 type descriptors entirely
    skip_patterns = [
        "function-wrap[",
        "lax-or-strict[",
        "json-or-python[",
        "function-after[",
        "union[",
    ]
    for pattern in skip_patterns:
        if pattern in item_str:
            return (None, False)

    # Handle patterns like '1.str', '1.list[Attachment][0]', '1.constrained-str'
    if item_str and item_str[0].isdigit():
        parts = item_str.split(".", 1)
        if len(parts) == 1:
            # Just a number like '1' - this is a positional argument index
            return (None, False)

        # We have something like '1.str' or '1.list[Attachment][0]'
        type_part = parts[1]

        # Check if it's a simple type to skip
        if type_part in {"str", "constrained-str"}:
            return (None, False)

        # Extract useful info from type patterns like 'list[Attachment][0]'
        extracted = _extract_field_from_type_loc(type_part)
        if extracted:
            return (extracted.strip("[]"), True)

        return (None, False)

    return (item_str, False)


def wrap_error(e: ValidationError) -> str:
    tabulation = get_tabulation()
    error_messages = defaultdict(list)

    for error in e.errors():
        errors_list = list(error["loc"])

        # Remove internal markers
        if "__root__" in errors_list:
            errors_list.remove("__root__")

        # Clean up Pydantic v2 location items
        cleaned_list = []
        for i, item in enumerate(errors_list):
            cleaned, is_index = _clean_loc_item(item, is_first=(i == 0))
            if cleaned is not None:
                if is_index or isinstance(item, int):
                    cleaned_list.append(f"[{cleaned}]")
                elif i == 0 or not cleaned_list:
                    cleaned_list.append(cleaned)
                else:
                    cleaned_list.append(f".{cleaned}")

        field_name = "".join(cleaned_list) if cleaned_list else "value"
        error_messages[field_name].append(error["msg"])

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
