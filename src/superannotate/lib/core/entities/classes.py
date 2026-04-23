from __future__ import annotations

from enum import Enum
from typing import Any

from lib.core.entities.base import HexColor
from lib.core.entities.base import TimedBaseModel
from lib.core.enums import ClassTypeEnum
from pydantic import ConfigDict
from pydantic import Field
from pydantic import StrictInt
from pydantic import StrictStr

DATE_REGEX = r"\d{4}-[01]\d-[0-3]\dT[0-2]\d:[0-5]\d:[0-5]\d(?:\.\d{3})Z"
DATE_TIME_FORMAT_ERROR_MESSAGE = (
    "does not match expected format YYYY-MM-DDTHH:MM:SS.fffZ"
)


class GroupTypeEnum(str, Enum):
    RADIO = "radio"
    CHECKLIST = "checklist"
    NUMERIC = "numeric"
    TEXT = "text"
    OCR = "ocr"


class Attribute(TimedBaseModel):
    model_config = ConfigDict(extra="ignore")

    id: StrictInt | None = None
    group_id: StrictInt | None = None
    project_id: StrictInt | None = None
    name: StrictStr | None = None
    default: Any = None

    def __hash__(self):
        return hash(f"{self.id}{self.group_id}{self.name}")


class AttributeGroup(TimedBaseModel):
    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    id: StrictInt | None = None
    group_type: GroupTypeEnum | None = None
    class_id: StrictInt | None = None
    name: StrictStr | None = None
    isRequired: bool = Field(default=False)
    attributes: list[Attribute] | None = None
    default_value: Any = None

    def __hash__(self):
        return hash(f"{self.id}{self.class_id}{self.name}")


class AnnotationClassEntity(TimedBaseModel):
    model_config = ConfigDict(
        extra="ignore",
        validate_assignment=True,
        json_encoders={HexColor: lambda v: v.__root__, Enum: lambda v: v.value},
    )

    id: StrictInt | None = None
    project_id: StrictInt | None = None
    type: ClassTypeEnum = ClassTypeEnum.OBJECT
    name: StrictStr
    color: HexColor
    attribute_groups: list[AttributeGroup] = Field(default_factory=list)

    def __hash__(self):
        return hash(f"{self.id}{self.type}{self.name}")
