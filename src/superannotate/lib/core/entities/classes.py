from datetime import datetime
from enum import Enum
from typing import Any
from typing import List
from typing import Optional

from lib.core.entities.base import BaseModel
from lib.core.enums import BaseTitledEnum
from lib.core.enums import ClassTypeEnum
from pydantic import BaseModel as BasePydanticModel
from pydantic import Extra
from pydantic import Field
from pydantic import StrictInt
from pydantic import StrictStr
from pydantic import validator
from pydantic.color import Color
from pydantic.color import ColorType
from pydantic.datetime_parse import parse_datetime

DATE_REGEX = r"\d{4}-[01]\d-[0-3]\dT[0-2]\d:[0-5]\d:[0-5]\d(?:\.\d{3})Z"
DATE_TIME_FORMAT_ERROR_MESSAGE = (
    "does not match expected format YYYY-MM-DDTHH:MM:SS.fffZ"
)


class HexColor(BasePydanticModel):
    __root__: ColorType

    @validator("__root__", pre=True)
    def validate_color(cls, v):
        return "#{:02X}{:02X}{:02X}".format(*Color(v).as_rgb_tuple())


class GroupTypeEnum(str, Enum):
    RADIO = "radio"
    CHECKLIST = "checklist"
    NUMERIC = "numeric"
    TEXT = "text"


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

    class Config:
        extra = Extra.allow

    def __hash__(self):
        return hash(f"{self.id}{self.group_id}{self.name}")


class AttributeGroup(TimedBaseModel):
    id: Optional[StrictInt]
    group_type: Optional[GroupTypeEnum]
    class_id: Optional[StrictInt]
    name: Optional[StrictStr]
    is_multiselect: Optional[bool]
    attributes: Optional[List[Attribute]]
    default_value: Any

    class Config:
        extra = Extra.allow
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
        extra = Extra.allow
        json_encoders = {
            HexColor: lambda v: v.__root__,
            BaseTitledEnum: lambda v: v.value,
        }
        validate_assignment = True
        use_enum_names = True
