import datetime
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import constr
from pydantic import EmailStr
from pydantic import Field


NotEmptyStr = constr(strict=True, min_length=1)


class Attribute(BaseModel):
    id: int
    group_id: int
    name: NotEmptyStr
    groupName: NotEmptyStr


class AttributeGroup(BaseModel):
    name: NotEmptyStr
    is_multiselect: Optional[int] = False
    attributes: List[Attribute]


class VectorAnnotationType(str, Enum):
    BBOX = "bbox"
    ELLIPSE = "ellipse"
    TEMPLATE = "template"
    CUBOID = "cuboid"
    POLYLINE = "polyline",
    POLYGON = "polygon"
    POINT = "point"


class BboxPoints(BaseModel):
    x1: float
    x2: float
    y1: float
    y2: float


class TimedBaseModel(BaseModel):
    created_at: datetime = Field(None, alias="createdAt")
    updated_at: datetime = Field(None, alias="updatedAt")


class UserAction(BaseModel):
    email: EmailStr
    role: str


class TrackableBaseModel(BaseModel):
    created_by: Optional[UserAction] = Field(None, alias="createdBy")
    updated_by: Optional[UserAction] = Field(None, alias="updatedBy")


class PointLabels(BaseModel):
    __root__: Dict[constr(regex=r"^[0-9]*$"), str]


class Correspondence(BaseModel):
    text: str
    email: EmailStr


class Comment(TimedBaseModel, UserAction):
    x: float
    y: float
    resolved: bool
    creation_type: str = Field(None, alias="creationType")
    correspondence: List[Correspondence]


class BaseSchema(TimedBaseModel):
    creation_type: str = Field(None, alias="creationType")
    class_id: int = Field(None, alias="ClassId")
    visible: Optional[bool]
    probability: Optional[int]
    locked: Optional[int]


class BaseInstance(BaseSchema):
    type: VectorAnnotationType
    groupId: Optional[int]
    attributes: List[Attribute]
    tracking_id: bool = Field(None, alias="trackingId")

    class Config:
        error_msg_templates = {
            'value_error.missing': f'field required for annotation',
        }


class Metadata(BaseModel):
    name: Optional[NotEmptyStr]
    width: Optional[int]
    height: Optional[int]
    status: str
    pinned: Optional[bool]
    isPredicted: Optional[bool]
    annotatorEmail: Optional[str]
    qaEmail: Optional[str]
