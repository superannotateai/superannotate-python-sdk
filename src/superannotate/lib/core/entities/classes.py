from datetime import datetime
from enum import Enum
from typing import Any
from typing import List
from typing import Optional

from lib.core.entities.base import BaseModel
from lib.core.entities.base import parse_datetime
from lib.core.enums import BaseTitledEnum
from lib.core.enums import ClassTypeEnum
from lib.core.pydantic_v1 import Color
from lib.core.pydantic_v1 import ColorType
from lib.core.pydantic_v1 import Extra
from lib.core.pydantic_v1 import Field
from lib.core.pydantic_v1 import StrictInt
from lib.core.pydantic_v1 import StrictStr
from lib.core.pydantic_v1 import validator

DATE_REGEX = r"\d{4}-[01]\d-[0-3]\dT[0-2]\d:[0-5]\d:[0-5]\d(?:\.\d{3})Z"
DATE_TIME_FORMAT_ERROR_MESSAGE = (
    "does not match expected format YYYY-MM-DDTHH:MM:SS.fffZ"
)


class HexColor(BaseModel):
    __root__: ColorType

    @validator("__root__", pre=True)
    def validate_color(cls, v):
        return "#{:02X}{:02X}{:02X}".format(*Color(v).as_rgb_tuple())


class GroupTypeEnum(str, Enum):
    RADIO = "radio"
    CHECKLIST = "checklist"
    NUMERIC = "numeric"
    TEXT = "text"
    OCR = "ocr"


class StringDate(datetime):
    @classmethod
    def __get_validators__(cls):
        yield parse_datetime
        yield cls.validate

    @classmethod
    def validate(cls, v: datetime):
        return v.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class TimedBaseModel(BaseModel):
    createdAt: StringDate = Field(None, alias="createdAt")
    updatedAt: StringDate = Field(None, alias="updatedAt")


class Attribute(TimedBaseModel):
    id: Optional[StrictInt]
    group_id: Optional[StrictInt]
    project_id: Optional[StrictInt]
    name: Optional[StrictStr]
    default: Any

    class Config:
        extra = Extra.ignore

    def __hash__(self):
        return hash(f"{self.id}{self.group_id}{self.name}")


class AttributeGroup(TimedBaseModel):
    id: Optional[StrictInt]
    group_type: Optional[GroupTypeEnum]
    class_id: Optional[StrictInt]
    name: Optional[StrictStr]
    isRequired: bool = Field(default=False)
    attributes: Optional[List[Attribute]]
    default_value: Any

    class Config:
        extra = Extra.ignore
        use_enum_values = True

    def __hash__(self):
        return hash(f"{self.id}{self.class_id}{self.name}")


class AnnotationClassEntity(TimedBaseModel):
    id: Optional[StrictInt]
    project_id: Optional[StrictInt]
    type: ClassTypeEnum = ClassTypeEnum.OBJECT
    name: StrictStr
    color: HexColor
    attribute_groups: List[AttributeGroup] = []

    def __hash__(self):
        return hash(f"{self.id}{self.type}{self.name}")

    class Config:
        extra = Extra.ignore
        json_encoders = {
            HexColor: lambda v: v.__root__,
            BaseTitledEnum: lambda v: v.value,
        }
        validate_assignment = True
        use_enum_names = True
