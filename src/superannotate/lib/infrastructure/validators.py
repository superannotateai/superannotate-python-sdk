import os
import typing
from collections import defaultdict

from pydantic import ValidationError
from pydantic import validators
from pydantic.errors import WrongConstantError


def wrong_constant_error(self):
    permitted = ", ".join(repr(v) for v in self.permitted)  # type: ignore
    return f"Available values are {permitted}."


WrongConstantError.__str__ = wrong_constant_error


def make_literal_validator(
    type_: typing.Any,
) -> typing.Callable[[typing.Any], typing.Any]:
    """
    Adding ability to input literal in the lower case.
    """
    permitted_choices = validators.all_literal_values(type_)
    allowed_choices = {v.lower() if v else v: v for v in permitted_choices}

    def literal_validator(v: typing.Any) -> typing.Any:
        try:
            return allowed_choices[v.lower()]
        except KeyError:
            raise WrongConstantError(given=v, permitted=permitted_choices)

    return literal_validator


def make_typeddict_validator(
    typeddict_cls: typing.Type["TypedDict"], config: typing.Type["BaseConfig"]  # type: ignore[valid-type]
) -> typing.Callable[[typing.Any], typing.Dict[str, typing.Any]]:
    """
    Wrapping to ignore extra keys
    """
    from pydantic.annotated_types import create_model_from_typeddict
    from pydantic import Extra

    config.extra = Extra.ignore

    TypedDictModel = create_model_from_typeddict(
        typeddict_cls,
        __config__=config,
        __module__=typeddict_cls.__module__,
    )
    typeddict_cls.__pydantic_model__ = TypedDictModel  # type: ignore[attr-defined]

    def typeddict_validator(values: "TypedDict") -> typing.Dict[str, typing.Any]:  # type: ignore[valid-type]
        return TypedDictModel.parse_obj(values).dict(exclude_unset=True)

    return typeddict_validator


validators.make_literal_validator = make_literal_validator
validators.make_typeddict_validator = make_typeddict_validator


def get_tabulation() -> int:
    try:
        return int(os.get_terminal_size().columns / 2)
    except OSError:
        return 48


def wrap_error(e: ValidationError) -> str:
    tabulation = get_tabulation()
    error_messages = defaultdict(list)
    for error in e.errors():
        errors_list = list(error["loc"])
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
