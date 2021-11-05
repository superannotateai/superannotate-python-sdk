import re
from datetime import datetime
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from pydantic import BaseModel
from pydantic import constr
from pydantic import EmailStr
from pydantic import Field
from pydantic.error_wrappers import ErrorWrapper
from pydantic.error_wrappers import ValidationError

NotEmptyStr = constr(strict=True, min_length=1)


class VectorAnnotationTypeEnum(str, Enum):
    BBOX = "bbox"
    ELLIPSE = "ellipse"
    TEMPLATE = "template"
    CUBOID = "cuboid"
    POLYLINE = ("polyline",)
    POLYGON = "polygon"
    POINT = "point"
    RBBOX = "rbbox"


class CreationTypeEnum(str, Enum):
    MANUAL = "Manual"
    PREDICTION = "Prediction"
    PRE_ANNOTATION = "Pre-annotation"


class AnnotationStatusEnum(str, Enum):
    NOT_STARTED = "NotStarted"
    IN_PROGRESS = "InProgress"
    QUALITY_CHECK = "QualityCheck"
    RETURNED = "Returned"
    COMPLETED = "Completed"
    SKIPPED = "Skipped"


class BaseRoleEnum(str, Enum):
    ADMIN = "Admin"
    ANNOTATOR = "Annotator"
    QA = "QA"


class BaseImageRoleEnum(str, Enum):
    CUSTOMER = "Customer"


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


class BboxPoints(BaseModel):
    x1: float
    x2: float
    y1: float
    y2: float


class TimedBaseModel(BaseModel):
    # TODO change to datetime
    created_at: datetime = Field(None, alias="createdAt")
    updated_at: datetime = Field(None, alias="updatedAt")


class UserAction(BaseModel):
    email: EmailStr
    role: BaseImageRoleEnum


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
    width: Optional[int]
    height: Optional[int]
    project_id: Optional[int] = Field(None, alias="projectId")
    annotator_email: Optional[EmailStr] = Field(None, alias="annotatorEmail")
    qa_email: Optional[EmailStr] = Field(None, alias="qaEmail")


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
            "value_error.missing": "field required for annotation",
        }


class BaseVectorInstance(BaseImageInstance):
    type: VectorAnnotationTypeEnum
    point_labels: Optional[PointLabels] = Field(None, alias="pointLabels")
    tracking_id: Optional[str] = Field(None, alias="trackingId")
    group_id: Optional[int] = Field(None, alias="groupId")


class Metadata(MetadataBase):
    name: NotEmptyStr
    status: Optional[AnnotationStatusEnum]
    pinned: Optional[bool]
    is_predicted: Optional[bool] = Field(None, alias="isPredicted")


class hex_color(NotEmptyStr):
    @classmethod
    def validate(cls, value: str) -> Union[str]:
        match = re.search(r"^#(?:[0-9a-fA-F]{3}){1,2}$", value)
        if not match:
            raise ValidationError(
                [
                    ErrorWrapper(
                        TypeError(f"invalid value for hex color {value}"), "type"
                    )
                ],
                cls,
            )
        return value
