# from typing import Literal
from pydantic.typing import Literal

from superannotate import enums
from superannotate import SAClient
from superannotate.lib.app.interface.types import validate_arguments



@validate_arguments
def foo(status: enums.ProjectStatus):
    return status


def test_enum_arg():
    SAClient()
    assert foo(1) == 1
    assert foo("NotStarted") == 1
    assert foo(enums.ProjectStatus.NotStarted.name) == 1
    assert foo(enums.ProjectStatus.NotStarted.value) == 1
