from datetime import datetime
from enum import Enum
from typing import Annotated
from typing import Any
from typing import List
from typing import Optional
from typing import Union

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import RootModel
from pydantic import StrictInt
from pydantic import StrictStr
from pydantic import field_validator
from pydantic.functional_validators import BeforeValidator
from pydantic_extra_types.color import Color

from lib.core.enums import ClassTypeEnum

DATE_REGEX = r"\d{4}-[01]\d-[0-3]\dT[0-2]\d:[0-5]\d:[0-5]\d(?:\.\d{3})Z"
DATE_TIME_FORMAT_ERROR_MESSAGE = (
    "does not match expected format YYYY-MM-DDTHH:MM:SS.fffZ"
)

ColorType = Union[Color, str, tuple]


def _validate_hex_color(v: Any) -> str:
    """Validate and convert color to hex format."""
    if isinstance(v, str) and v.startswith("#"):
        return v
    return "#{:02X}{:02X}{:02X}".format(*Color(v).as_rgb_tuple())


class HexColor(RootModel[str]):
    """Hex color model."""

    root: str

    @field_validator("root", mode="before")
    @classmethod
    def validate_color(cls, v):
        return _validate_hex_color(v)


class GroupTypeEnum(str, Enum):
    RADIO = "radio"
    CHECKLIST = "checklist"
    NUMERIC = "numeric"
    TEXT = "text"
    OCR = "ocr"


def _parse_string_date_classes(v: Any) -> Optional[str]:
    """Parse datetime to string format for classes."""
    if v is None:
        return None
    if isinstance(v, str):
        return v
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    try:
        from dateutil.parser import parse

        dt = parse(str(v))
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    except Exception:
        return str(v)


StringDate = Annotated[Optional[str], BeforeValidator(_parse_string_date_classes)]


class TimedBaseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    createdAt: StringDate = Field(default=None, alias="createdAt")
    updatedAt: StringDate = Field(default=None, alias="updatedAt")


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
    )

    id: Optional[StrictInt] = None
    project_id: Optional[StrictInt] = None
    type: ClassTypeEnum = ClassTypeEnum.OBJECT
    name: StrictStr
    color: HexColor
    attribute_groups: List[AttributeGroup] = []

    def __hash__(self):
        return hash(f"{self.id}{self.type}{self.name}")
