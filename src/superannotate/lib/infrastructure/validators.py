import os
from collections import defaultdict

from pydantic import ValidationError


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
