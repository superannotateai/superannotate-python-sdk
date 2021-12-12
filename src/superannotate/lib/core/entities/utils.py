from enum import Enum
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel as PyDanticBaseModel
from pydantic import conlist
from pydantic import constr
from pydantic import EmailStr
from pydantic import Extra
from pydantic import Field
from pydantic import StrictBool
from pydantic import StrictInt
from pydantic import StrictStr
from pydantic import StrRegexError
from pydantic import ValidationError
from pydantic import validator
from pydantic.error_wrappers import ErrorWrapper
from pydantic.errors import EnumMemberError


def enum_error_handling(self) -> str:
    permitted = ", ".join(repr(v.value) for v in self.enum_values)
    return f"Invalid value, permitted: {permitted}"


EnumMemberError.__str__ = enum_error_handling

NotEmptyStr = constr(strict=True, min_length=1)

DATE_REGEX = r"\d{4}-[01]\d-[0-3]\dT[0-2]\d:[0-5]\d:[0-5]\d(?:\.\d{3})Z"

DATE_TIME_FORMAT_ERROR_MESSAGE = (
    "does not match expected format YYYY-MM-DDTHH:MM:SS.fffZ"
)

POINT_LABEL_KEY_FORMAT_ERROR_MESSAGE = "does not match expected format ^[0-9]+$"

POINT_LABEL_VALUE_FORMAT_ERROR_MESSAGE = "str type expected"

INVALID_DICT_MESSAGE = "value is not a valid dict"


class BaseModel(PyDanticBaseModel):
    class Config:
        extra = Extra.allow
        use_enum_values = True
        error_msg_templates = {
            "type_error.integer": "integer type expected",
            "type_error.string": "str type expected",
            "value_error.missing": "field required",
        }


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
    PRE_ANNOTATION = "Preannotation"


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
    id: Optional[StrictInt]
    group_id: Optional[StrictInt] = Field(None, alias="groupId")
    name: NotEmptyStr
    group_name: NotEmptyStr = Field(alias="groupName")


class Tag(BaseModel):
    __root__: NotEmptyStr


class AttributeGroup(BaseModel):
    name: NotEmptyStr
    # TODO :
    is_multiselect: Optional[int] = False
    attributes: List[Attribute]


class BboxPoints(BaseModel):
    x1: float
    x2: float
    y1: float
    y2: float


class TimedBaseModel(BaseModel):
    created_at: Optional[constr(regex=DATE_REGEX)] = Field(None, alias="createdAt")
    updated_at: Optional[constr(regex=DATE_REGEX)] = Field(None, alias="updatedAt")

    @validator("created_at", "updated_at", pre=True)
    def validate_created_at(cls, value):
        try:
            if value is not None:
                constr(regex=DATE_REGEX).validate(value)
        except (TypeError, StrRegexError):
            raise TypeError(DATE_TIME_FORMAT_ERROR_MESSAGE)
        return value


class UserAction(BaseModel):
    email: EmailStr
    role: BaseImageRoleEnum


class TrackableModel(BaseModel):
    created_by: Optional[UserAction] = Field(None, alias="createdBy")
    updated_by: Optional[UserAction] = Field(None, alias="updatedBy")
    creation_type: Optional[CreationTypeEnum] = Field(
        CreationTypeEnum.PRE_ANNOTATION.value, alias="creationType"
    )

    @validator("creation_type", always=True)
    def clean_creation_type(cls, _):
        return CreationTypeEnum.PRE_ANNOTATION.value


class LastUserAction(BaseModel):
    email: EmailStr
    timestamp: StrictInt


class BaseInstance(TrackableModel, TimedBaseModel):
    class_id: Optional[StrictInt] = Field(None, alias="classId")
    class_name: Optional[NotEmptyStr] = Field(None, alias="className")


class MetadataBase(BaseModel):
    url: Optional[StrictStr]
    name: NotEmptyStr
    last_action: Optional[LastUserAction] = Field(None, alias="lastAction")
    width: Optional[StrictInt]
    height: Optional[StrictInt]
    project_id: Optional[StrictInt] = Field(None, alias="projectId")
    annotator_email: Optional[EmailStr] = Field(None, alias="annotatorEmail")
    qa_email: Optional[EmailStr] = Field(None, alias="qaEmail")
    status: Optional[AnnotationStatusEnum]


class Correspondence(BaseModel):
    text: NotEmptyStr
    email: EmailStr


class Comment(TimedBaseModel, TrackableModel):
    x: float
    y: float
    resolved: Optional[StrictBool] = Field(False)
    correspondence: conlist(Correspondence, min_items=1)


class BaseImageInstance(BaseInstance):
    visible: Optional[StrictBool]
    locked: Optional[StrictBool]
    probability: Optional[StrictInt] = Field(100)
    attributes: Optional[List[Attribute]] = Field(list())
    error: Optional[StrictBool]

    class Config:
        error_msg_templates = {
            "value_error.missing": "field required for annotation",
        }


class StringA(BaseModel):
    string: StrictStr


class PointLabels(BaseModel):
    __root__: Dict[constr(regex=r"^[0-9]+$"), StrictStr]  # noqa F722

    @classmethod
    def __get_validators__(cls):
        yield cls.validate_type
        yield cls.validate_value

    @validator("__root__", pre=True)
    def validate_value(cls, values):
        result = {}
        errors = []
        validate_key = None
        validate_value = None
        for key, value in values.items():
            try:
                validate_key = constr(regex=r"^[0-9]+$", min_length=1).validate(key)
            except ValueError:
                errors.append(
                    ErrorWrapper(
                        ValueError(POINT_LABEL_KEY_FORMAT_ERROR_MESSAGE), str(key)
                    )
                )
            try:
                validate_value = StringA(string=value)
            except ValueError:
                errors.append(
                    ErrorWrapper(
                        ValueError(POINT_LABEL_VALUE_FORMAT_ERROR_MESSAGE), str(key)
                    )
                )

        if validate_key and validate_value:
            result.update({key: value})

        if errors:
            raise ValidationError(errors, cls)
        return result

    @classmethod
    def validate_type(cls, values):
        if not issubclass(type(values), dict):
            raise TypeError(INVALID_DICT_MESSAGE)
        return values


class BaseVectorInstance(BaseImageInstance):
    type: VectorAnnotationTypeEnum
    point_labels: Optional[PointLabels] = Field(None, alias="pointLabels")
    tracking_id: Optional[StrictStr] = Field(None, alias="trackingId")
    group_id: Optional[StrictInt] = Field(None, alias="groupId")


class Metadata(MetadataBase):
    pinned: Optional[StrictBool]
    is_predicted: Optional[StrictBool] = Field(None, alias="isPredicted")
