
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
    group_id: int = Field(alias="groupId")
    # only in export
    # name: NotEmptyStr
    # group_name: NotEmptyStr = Field(None, alias="groupName")


class Tag(BaseModel):
    __root__: str


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
    # TODO change to datetime
    created_at: int = Field(None, alias="createdAt")
    updated_at: int = Field(None, alias="updatedAt")


class UserAction(BaseModel):
    email: EmailStr
    role: str


class LastUserAction(BaseModel):
    email: EmailStr
    timestamp: float


class BaseInstance(BaseModel):
    # TODO change to datetime
    class_id: int = Field(alias="classId")
    created_at: Optional[int] = Field(None, alias="createdAt")
    created_by: Optional[UserAction] = Field(None, alias="createdBy")
    creation_type: Optional[NotEmptyStr] = Field(None, alias="creationType")
    updated_at: Optional[int] = Field(None, alias="updatedAt")
    updated_by: Optional[UserAction] = Field(None, alias="updatedBy")


class MetadataBase(BaseModel):
    last_action: Optional[LastUserAction] = Field(None, alias="lastAction")


class PointLabels(BaseModel):
    __root__: Dict[constr(regex=r"^[0-9]*$"), str]


class Correspondence(BaseModel):
    text: str
    email: EmailStr


class Comment(TimedBaseModel, UserAction):
    x: float
    y: float
    resolved: bool
    creation_type: str = Field(alias="creationType")
    correspondence: List[Correspondence]


class BaseImageInstance(BaseInstance):
    visible: Optional[bool]
    probability: Optional[int]
    locked: Optional[int]
    type: VectorAnnotationType
    group_id: Optional[int] = Field(None, alias="groupId")
    attributes: List[Attribute]
    tracking_id: bool = Field(alias="trackingId")

    class Config:
        error_msg_templates = {
            'value_error.missing': f'field required for annotation',
        }


class Metadata(MetadataBase):
    name: Optional[NotEmptyStr]
    width: Optional[int]
    height: Optional[int]
    status: str
    pinned: Optional[bool]
    is_predicted: Optional[bool] = Field(None, alias="isPredicted")
    # annotator_email: Optional[EmailStr] = Field(None, alias="annotatorEmail")
    # qa_email: Optional[EmailStr] = Field(None, alias="qaEmail")


