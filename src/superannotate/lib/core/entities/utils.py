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
    id: Optional[int]
    group_id: Optional[int] = Field(None, alias="groupId")
    name: NotEmptyStr
    group_name: NotEmptyStr = Field(None, alias="groupName")


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
    RBBOX = "rbbox"


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


class CreationType(BaseModel):
    __root__: str = Field(alias="creationType")


class TrackableModel(BaseModel):
    created_by: Optional[UserAction] = Field(None, alias="createdBy")
    updated_by: Optional[UserAction] = Field(None, alias="updatedBy")
    creation_type: Optional[CreationType]


class LastUserAction(BaseModel):
    email: EmailStr
    timestamp: float


class BaseInstance(TrackableModel, TimedBaseModel):
    # TODO check id: Optional[str]
    # TODO change to datetime
    class_id: int = Field(alias="classId")


class MetadataBase(BaseModel):
    last_action: Optional[LastUserAction] = Field(None, alias="lastAction")


class PointLabels(BaseModel):
    __root__: Dict[constr(regex=r"^[0-9]*$"), str]  # noqa: F722 E261


class Correspondence(BaseModel):
    text: NotEmptyStr
    email: EmailStr


class Comment(TimedBaseModel, TrackableModel):
    x: float
    y: float
    resolved: Optional[bool] = Field(False)
    correspondence: Optional[List[Correspondence]]


class BaseImageInstance(BaseInstance):
    class_id: Optional[int] = Field(None, alias="classId")
    visible: Optional[bool]
    locked: Optional[bool]
    probability: Optional[int]  # TODO check = Field(100)
    attributes: List[Attribute]
    error: Optional[bool]  # todo check

    class Config:
        error_msg_templates = {
            'value_error.missing': 'field required for annotation',
        }


class BaseVectorInstance(BaseImageInstance):
    type: VectorAnnotationType
    point_labels: Optional[PointLabels] = Field(None, alias="pointLabels")
    tracking_id: Optional[str] = Field(None, alias="trackingId")
    group_id: Optional[int] = Field(None, alias="groupId")


class Metadata(MetadataBase):
    name: NotEmptyStr
    width: Optional[int]
    height: Optional[int]
    status: Optional[str]
    pinned: Optional[bool]
    is_predicted: Optional[bool] = Field(None, alias="isPredicted")
    annotator_email: Optional[EmailStr] = Field(None, alias="annotatorEmail")
    qa_email: Optional[EmailStr] = Field(None, alias="qaEmail")
