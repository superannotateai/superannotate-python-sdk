from enum import Enum
from typing import Any
from typing import List
from typing import Optional

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

    id: Optional[StrictInt] = None
    group_id: Optional[StrictInt] = None
    project_id: Optional[StrictInt] = None
    name: Optional[StrictStr] = None
    default: Any = None

    def __hash__(self):
        return hash(f"{self.id}{self.group_id}{self.name}")


class AttributeGroup(TimedBaseModel):
    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    id: Optional[StrictInt] = None
    group_type: Optional[GroupTypeEnum] = None
    class_id: Optional[StrictInt] = None
    name: Optional[StrictStr] = None
    isRequired: bool = Field(default=False)
    attributes: Optional[List[Attribute]] = None
    default_value: Any = None

    def __hash__(self):
        return hash(f"{self.id}{self.class_id}{self.name}")


class AnnotationClassEntity(TimedBaseModel):
    model_config = ConfigDict(
        extra="ignore",
        validate_assignment=True,
        json_encoders={HexColor: lambda v: v.__root__, Enum: lambda v: v.value},
    )

    id: Optional[StrictInt] = None
    project_id: Optional[StrictInt] = None
    type: ClassTypeEnum = ClassTypeEnum.OBJECT
    name: StrictStr
    color: HexColor
    attribute_groups: List[AttributeGroup] = Field(default_factory=list)

    def __hash__(self):
        return hash(f"{self.id}{self.type}{self.name}")
