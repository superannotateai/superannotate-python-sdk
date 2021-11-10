from datetime import datetime
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel as PyDanticBaseModel
from pydantic import conlist
from pydantic import constr
from pydantic import EmailStr
from pydantic import Field
from pydantic import validator
from pydantic.color import Color
from pydantic.color import ColorType
from pydantic.datetime_parse import parse_datetime


NotEmptyStr = constr(strict=True, min_length=1)


class BaseModel(PyDanticBaseModel):
    class Config:
        use_enum_values = True
        error_msg_templates = {
            "type_error.integer": "integer type expected",
            "type_error.string": "str type expected",
            "value_error.missing": "field required",
        }


class StringDate(datetime):
    @classmethod
    def __get_validators__(cls):
        yield parse_datetime
        yield cls.validate

    @classmethod
    def validate(cls, v: datetime):
        return f'{v.replace(tzinfo=None).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]}Z'


class VectorAnnotationTypeEnum(str, Enum):
    BBOX = "bbox"
    ELLIPSE = "ellipse"
    TEMPLATE = "template"
    CUBOID = "cuboid"
    POLYLINE = "polyline"
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
    ADMIN = "Admin"
    ANNOTATOR = "Annotator"
    QA = "QA"


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
    created_at: StringDate = Field(None, alias="createdAt")
    updated_at: StringDate = Field(None, alias="updatedAt")


class UserAction(BaseModel):
    email: EmailStr
    role: BaseImageRoleEnum


class TrackableModel(BaseModel):
    created_by: Optional[UserAction] = Field(None, alias="createdBy")
    updated_by: Optional[UserAction] = Field(None, alias="updatedBy")
    creation_type: Optional[CreationTypeEnum] = Field(CreationTypeEnum.PRE_ANNOTATION.value, alias="creationType")

    @validator("creation_type")
    def clean_creation_type(cls, value):
        return value or CreationTypeEnum.PRE_ANNOTATION.value


class LastUserAction(BaseModel):
    email: EmailStr
    timestamp: float


class BaseInstance(TrackableModel, TimedBaseModel):
    class_id: Optional[str] = Field(None, alias="classId")
    class_name: Optional[str] = Field(None, alias="className")


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
    correspondence: conlist(Correspondence, min_items=1)


class BaseImageInstance(BaseInstance):
    class_id: Optional[int] = Field(None, alias="classId")
    class_name: Optional[str] = Field(None, alias="className")
    visible: Optional[bool]
    locked: Optional[bool]
    probability: Optional[int] = Field(100)
    attributes: Optional[List[Attribute]] = Field(list())
    error: Optional[bool]

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


class PixelColor(BaseModel):
    __root__: ColorType

    @validator("__root__")
    def validate_color(cls, v):
        color = Color(v)
        return color.as_hex()