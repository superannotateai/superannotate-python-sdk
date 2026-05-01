from __future__ import annotations

from enum import auto
from enum import Enum
from typing import Any

from lib.core.entities.base import HexColor
from lib.core.entities.base import TimedBaseModel
from lib.core.enums import WMClassTypeEnum
from lib.core.enums import WMGroupTypeEnum
from lib.core.enums import WMUserStateEnum
from lib.core.exceptions import AppException
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_serializer
from pydantic import field_validator
from pydantic import model_validator
from pydantic import StrictInt
from pydantic import StrictStr


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


class WMProjectEntity(TimedBaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int | None = None
    team_id: int | None = None
    name: str
    type: ProjectType
    description: str | None = None
    creator_id: str | None = None
    status: ProjectStatus | None = None
    workflow_id: int | None = None
    sync_status: int | None = None
    upload_state: str | None = None
    custom_fields: dict | None = Field(default_factory=dict, alias="customField")

    @field_validator("custom_fields", mode="before")
    @classmethod
    def custom_fields_transformer(cls, v):
        if v and "custom_field_values" in v:
            return v.get("custom_field_values", {})
        return {}

    def __eq__(self, other):
        return self.id == other.id

    def model_dump_json(self, **kwargs):
        if "exclude" not in kwargs:
            kwargs["exclude"] = {"custom_fields"}
        return super().model_dump_json(**kwargs)


class WMUserEntity(TimedBaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int | None = None
    team_id: int | None = None
    role: WMUserTypeEnum
    email: str | None = None
    state: WMUserStateEnum | None = None
    custom_fields: dict | None = Field(default_factory=dict, alias="customField")

    @field_validator("custom_fields", mode="before")
    @classmethod
    def custom_fields_transformer(cls, v):
        if v and "custom_field_values" in v:
            return v.get("custom_field_values", {})
        return {}

    def model_dump_json(self, **kwargs):
        if "exclude" not in kwargs:
            kwargs["exclude"] = {"custom_fields"}
        return super().model_dump_json(**kwargs)


class WMProjectUserEntity(TimedBaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int | None = None
    team_id: int | None = None
    role: int | None = None
    email: str | None = None
    state: WMUserStateEnum | None = None
    custom_fields: dict | None = Field(default_factory=dict, alias="customField")
    permissions: dict | None = None
    categories: list[dict] | None = None

    @field_validator("custom_fields", mode="before")
    @classmethod
    def custom_fields_transformer(cls, v):
        if v and "custom_field_values" in v:
            return v.get("custom_field_values", {})
        return {}

    def model_dump_json(self, **kwargs):
        if "exclude" not in kwargs:
            kwargs["exclude"] = {"custom_fields"}
        return super().model_dump_json(**kwargs)


class WMScoreEntity(TimedBaseModel):
    id: int
    team_id: int
    name: str
    description: str | None = None
    type: str
    payload: dict | None = None


class TelemetryScoreEntity(BaseModel):
    item_id: int
    team_id: int
    project_id: int
    user_id: str
    user_role: str
    score_id: int
    value: Any | None = None
    weight: float | None = None


class ScoreEntity(TimedBaseModel):
    id: int
    name: str
    value: Any | None = None
    weight: float | None = None


class ScorePayloadEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_id: str
    value: Any = None
    weight: float | int | None = 1.0

    @field_validator("weight", mode="before")
    @classmethod
    def validate_weight(cls, v):
        if v is not None and (not isinstance(v, (int, float)) or v <= 0):
            raise AppException("Please provide a valid number greater than 0")
        return v

    @model_validator(mode="after")
    def check_weight_and_value(self):
        if (self.weight is None and self.value is not None) or (
            self.weight is not None and self.value is None
        ):
            raise AppException("Weight and Value must both be set or both be None.")
        return self


class WMAttribute(TimedBaseModel):
    model_config = ConfigDict(extra="ignore")

    id: StrictInt | None = None
    group_id: StrictInt | None = None
    project_id: StrictInt | None = None
    name: StrictStr | None = None
    default: Any = None

    def __hash__(self):
        return hash(f"{self.id}{self.group_id}{self.name}")


class WMAttributeGroup(TimedBaseModel):
    model_config = ConfigDict(extra="ignore")

    id: StrictInt | None = None
    group_type: WMGroupTypeEnum
    class_id: StrictInt | None = None
    name: StrictStr | None = None
    isRequired: bool = Field(default=False, alias="is_required")
    attributes: list[WMAttribute] | None = None
    default_value: Any = None

    def __hash__(self):
        return hash(f"{self.id}{self.class_id}{self.name}")

    @classmethod
    def _serialize_group_type(cls, v: WMGroupTypeEnum | None, _info):
        if v is None:
            return v
        if isinstance(v, WMGroupTypeEnum):
            return v
        if isinstance(v, str):
            # Try by value first (e.g., "radio")
            for member in WMGroupTypeEnum:
                if member.value == v.lower():
                    return member
            # Try by name (e.g., "RADIO" or "radio")
            try:
                return WMGroupTypeEnum[v.upper()]
            except KeyError:
                pass
        raise ValueError(f"Invalid group_type: {v}")

    @field_validator("group_type", mode="before")
    @classmethod
    def validate_group_type(cls, v):
        return cls._serialize_group_type(v, None)

    @field_serializer("group_type", when_used="json")
    def serialize_group_type(self, v: WMGroupTypeEnum):
        return v.name


class WMAnnotationClassEntity(TimedBaseModel):
    model_config = ConfigDict(
        extra="ignore", validate_assignment=True, arbitrary_types_allowed=True
    )

    id: StrictInt | None = None
    project_id: StrictInt | None = None
    type: WMClassTypeEnum = WMClassTypeEnum.OBJECT
    name: StrictStr
    color: HexColor
    attribute_groups: list[WMAttributeGroup] = Field(
        default_factory=list, alias="attributeGroups"
    )

    def __hash__(self):
        return hash(f"{self.id}{self.type}{self.name}")

    @field_serializer("type")
    def serialize_type(self, v: WMClassTypeEnum, _info):
        # API expects lowercase enum values (object, tag, etc.)
        return v.value

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, v):
        if isinstance(v, WMClassTypeEnum):
            return v
        if isinstance(v, str):
            # Try by value first (e.g., "object")
            for member in WMClassTypeEnum:
                if member.value == v:
                    return member
            # Try by name (e.g., "OBJECT")
            try:
                return WMClassTypeEnum[v.upper()]
            except KeyError:
                pass
        raise ValueError(f"Invalid type: {v}")
