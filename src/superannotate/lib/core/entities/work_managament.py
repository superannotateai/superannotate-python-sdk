import datetime
from enum import auto
from enum import Enum
from typing import Any
from typing import Optional
from typing import Union

from lib.core.entities.base import TimedBaseModel
from lib.core.enums import WMUserStateEnum
from lib.core.exceptions import AppException
from lib.core.pydantic_v1 import BaseModel
from lib.core.pydantic_v1 import Extra
from lib.core.pydantic_v1 import Field
from lib.core.pydantic_v1 import parse_datetime
from lib.core.pydantic_v1 import root_validator
from lib.core.pydantic_v1 import validator


class ProjectType(str, Enum):
    Vector = "VECTOR"
    Pixel = "PIXEL"
    Video = "PUBLIC_VIDEO"
    Document = "PUBLIC_TEXT"
    Tiled = "TILED"
    Other = "CLASSIFICATION"
    PointCloud = "POINT_CLOUD"
    Multimodal = "CUSTOM_LLM"


class WMUserTypeEnum(int, Enum):
    Contributor = 4
    TeamAdmin = 7
    TeamOwner = 12
    OrganizationAdmin = 15
    other = auto()


class ProjectStatus(str, Enum):
    Undefined = "undefined"
    NotStarted = "notStarted"
    InProgress = "inProgress"
    Completed = "completed"
    OnHold = "onHold"

    def __repr__(self):
        return self._name_


class StringDate(datetime.datetime):
    @classmethod
    def __get_validators__(cls):
        yield parse_datetime
        yield cls.validate

    @classmethod
    def validate(cls, v: datetime):
        v = v.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        return v


class WMProjectEntity(TimedBaseModel):
    id: Optional[int]
    team_id: Optional[int]
    name: str
    type: ProjectType
    description: Optional[str]
    creator_id: Optional[str]
    status: Optional[ProjectStatus]
    workflow_id: Optional[int]
    sync_status: Optional[int]
    upload_state: Optional[str]
    custom_fields: Optional[dict] = Field(dict(), alias="customField")

    @validator("custom_fields")
    def custom_fields_transformer(cls, v):
        if v and "custom_field_values" in v:
            return v.get("custom_field_values", {})
        return {}

    class Config:
        extra = Extra.ignore
        use_enum_names = True

        json_encoders = {
            Enum: lambda v: v.value,
            datetime.date: lambda v: v.isoformat(),
            datetime.datetime: lambda v: v.isoformat(),
        }

    def __eq__(self, other):
        return self.id == other.id

    def json(self, **kwargs):
        if "exclude" not in kwargs:
            kwargs["exclude"] = {"custom_fields"}
        return super().json(**kwargs)


class WMUserEntity(TimedBaseModel):
    id: Optional[int]
    team_id: Optional[int]
    role: WMUserTypeEnum
    email: Optional[str]
    state: Optional[WMUserStateEnum]
    custom_fields: Optional[dict] = Field(dict(), alias="customField")

    class Config:
        extra = Extra.ignore
        use_enum_names = True

        json_encoders = {
            Enum: lambda v: v.value,
            datetime.date: lambda v: v.isoformat(),
            datetime.datetime: lambda v: v.isoformat(),
        }

    @validator("custom_fields")
    def custom_fields_transformer(cls, v):
        if v and "custom_field_values" in v:
            return v.get("custom_field_values", {})
        return {}

    def json(self, **kwargs):
        if "exclude" not in kwargs:
            kwargs["exclude"] = {"custom_fields"}
        return super().json(**kwargs)


class WMProjectUserEntity(TimedBaseModel):
    id: Optional[int]
    team_id: Optional[int]
    role: int
    email: Optional[str]
    state: Optional[WMUserStateEnum]
    custom_fields: Optional[dict] = Field(dict(), alias="customField")

    class Config:
        extra = Extra.ignore
        use_enum_names = True

        json_encoders = {
            Enum: lambda v: v.value,
            datetime.date: lambda v: v.isoformat(),
            datetime.datetime: lambda v: v.isoformat(),
        }

    @validator("custom_fields")
    def custom_fields_transformer(cls, v):
        if v and "custom_field_values" in v:
            return v.get("custom_field_values", {})
        return {}

    def json(self, **kwargs):
        if "exclude" not in kwargs:
            kwargs["exclude"] = {"custom_fields"}
        return super().json(**kwargs)


class WMScoreEntity(TimedBaseModel):
    id: int
    team_id: int
    name: str
    description: Optional[str]
    type: str
    payload: Optional[dict]


class TelemetryScoreEntity(BaseModel):
    item_id: int
    team_id: int
    project_id: int
    user_id: str
    user_role: str
    score_id: int
    value: Optional[Any]
    weight: Optional[float]


class ScoreEntity(TimedBaseModel):
    id: int
    name: str
    value: Optional[Any]
    weight: Optional[float]


class ScorePayloadEntity(BaseModel):
    component_id: str
    value: Any
    weight: Optional[Union[float, int]] = 1.0

    class Config:
        extra = Extra.forbid

    @validator("weight", pre=True, always=True)
    def validate_weight(cls, v):
        if v is not None and (not isinstance(v, (int, float)) or v <= 0):
            raise AppException("Please provide a valid number greater than 0")
        return v

    @root_validator()
    def check_weight_and_value(cls, values):
        value = values.get("value")
        weight = values.get("weight")
        if (weight is None and value is not None) or (
            weight is not None and value is None
        ):
            raise AppException("Weight and Value must both be set or both be None.")
        return values
