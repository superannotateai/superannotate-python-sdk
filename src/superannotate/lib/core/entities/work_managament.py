import datetime
from enum import auto
from enum import Enum
from typing import Optional

from lib.core.entities.base import TimedBaseModel
from lib.core.enums import WMUserStateEnum
from lib.core.pydantic_v1 import Extra
from lib.core.pydantic_v1 import Field
from lib.core.pydantic_v1 import parse_datetime
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
