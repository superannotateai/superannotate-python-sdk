from enum import Enum
from typing import List
from typing import Optional

from lib.core.enums import BaseTitledEnum
from lib.core.enums import ClassTypeEnum
from pydantic import BaseModel as BasePydanticModel
from pydantic import Extra
from pydantic import StrictInt
from pydantic import StrictStr
from pydantic import validator
from pydantic.color import Color
from pydantic.color import ColorType


DATE_REGEX = r"\d{4}-[01]\d-[0-3]\dT[0-2]\d:[0-5]\d:[0-5]\d(?:\.\d{3})Z"
DATE_TIME_FORMAT_ERROR_MESSAGE = (
    "does not match expected format YYYY-MM-DDTHH:MM:SS.fffZ"
)


class HexColor(BasePydanticModel):
    __root__: ColorType

    @validator("__root__")
    def validate_color(cls, v):
        return "#{:02X}{:02X}{:02X}".format(*Color(v).as_rgb_tuple())


class BaseModel(BasePydanticModel):
    class Config:
        extra = Extra.allow
        error_msg_templates = {
            "type_error.integer": "integer type expected",
            "type_error.string": "str type expected",
            "value_error.missing": "field required",
        }

    def dict(self, *args, fill_enum_values=False, **kwargs):
        data = super().dict(*args, **kwargs)
        if fill_enum_values:
            data = self._fill_enum_values(data)
        return data

    @staticmethod
    def _fill_enum_values(data: dict) -> dict:
        for key, val in data.items():
            if isinstance(val, BaseTitledEnum):
                data[key] = val.__doc__
        return data


class GroupTypeEnum(str, Enum):
    RADIO = "radio"
    CHECKLIST = "checklist"
    NUMERIC = "numeric"
    TEXT = "text"


class Attribute(BaseModel):
    id: Optional[StrictInt]
    group_id: Optional[StrictInt]
    project_id: Optional[StrictInt]
    name: StrictStr

    def __hash__(self):
        return hash(f"{self.id}{self.group_id}{self.name}")


class AttributeGroup(BaseModel):
    id: Optional[StrictInt]
    group_type: Optional[GroupTypeEnum]
    class_id: Optional[StrictInt]
    name: StrictStr
    is_multiselect: Optional[bool]
    attributes: Optional[List[Attribute]]

    class Config:
        use_enum_values = True

    def __hash__(self):
        return hash(f"{self.id}{self.class_id}{self.name}")


class AnnotationClassEntity(BaseModel):
    id: Optional[StrictInt]
    project_id: Optional[StrictInt]
    type: ClassTypeEnum = ClassTypeEnum.OBJECT
    name: StrictStr
    color: HexColor
    attribute_groups: List[AttributeGroup] = []

    def __hash__(self):
        return hash(f"{self.id}{self.type}{self.name}")

    class Config:
        validate_assignment = True
        exclude_none = True
        fill_enum_values = True
