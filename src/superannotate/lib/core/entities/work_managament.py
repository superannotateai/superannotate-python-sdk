import datetime
from enum import auto
from enum import Enum
from typing import Annotated
from typing import Any
from typing import List
from typing import Optional
from typing import Union

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator
from pydantic.functional_validators import BeforeValidator

from lib.core.entities.base import TimedBaseModel
from lib.core.enums import WMUserStateEnum
from lib.core.exceptions import AppException


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


def _parse_string_date_wm(v: Any) -> Optional[str]:
    """Parse datetime to string format for work management."""
    if v is None:
        return None
    if isinstance(v, str):
        return v
    if isinstance(v, datetime.datetime):
        return v.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    try:
        from dateutil.parser import parse

        dt = parse(str(v))
        return dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    except Exception:
        return str(v)


StringDate = Annotated[Optional[str], BeforeValidator(_parse_string_date_wm)]


class WMProjectEntity(TimedBaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: Optional[int] = None
    team_id: Optional[int] = None
    name: str
    type: ProjectType
    description: Optional[str] = None
    creator_id: Optional[str] = None
    status: Optional[ProjectStatus] = None
    workflow_id: Optional[int] = None
    sync_status: Optional[int] = None
    upload_state: Optional[str] = None
    custom_fields: Optional[dict] = Field(default_factory=dict, alias="customField")

    @field_validator("custom_fields", mode="before")
    @classmethod
    def custom_fields_transformer(cls, v):
        if v and isinstance(v, dict) and "custom_field_values" in v:
            return v.get("custom_field_values", {})
        return {} if v is None else v

    def __eq__(self, other):
        return self.id == other.id

    def model_dump_json(self, **kwargs):
        if "exclude" not in kwargs:
            kwargs["exclude"] = {"custom_fields"}
        return super().model_dump_json(**kwargs)

    # Backward compatibility
    def json(self, **kwargs):
        return self.model_dump_json(**kwargs)


class WMUserEntity(TimedBaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: Optional[int] = None
    team_id: Optional[int] = None
    role: WMUserTypeEnum
    email: Optional[str] = None
    state: Optional[WMUserStateEnum] = None
    custom_fields: Optional[dict] = Field(default_factory=dict, alias="customField")

    @field_validator("custom_fields", mode="before")
    @classmethod
    def custom_fields_transformer(cls, v):
        if v and isinstance(v, dict) and "custom_field_values" in v:
            return v.get("custom_field_values", {})
        return {} if v is None else v

    def model_dump_json(self, **kwargs):
        if "exclude" not in kwargs:
            kwargs["exclude"] = {"custom_fields"}
        return super().model_dump_json(**kwargs)

    # Backward compatibility
    def json(self, **kwargs):
        return self.model_dump_json(**kwargs)


class WMProjectUserEntity(TimedBaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: Optional[int] = None
    team_id: Optional[int] = None
    role: Optional[int] = None
    email: Optional[str] = None
    state: Optional[WMUserStateEnum] = None
    custom_fields: Optional[dict] = Field(default_factory=dict, alias="customField")
    permissions: Optional[dict] = None
    categories: Optional[List[dict]] = None

    @field_validator("custom_fields", mode="before")
    @classmethod
    def custom_fields_transformer(cls, v):
        if v and isinstance(v, dict) and "custom_field_values" in v:
            return v.get("custom_field_values", {})
        return {} if v is None else v

    def model_dump_json(self, **kwargs):
        if "exclude" not in kwargs:
            kwargs["exclude"] = {"custom_fields"}
        return super().model_dump_json(**kwargs)

    # Backward compatibility
    def json(self, **kwargs):
        return self.model_dump_json(**kwargs)


class WMScoreEntity(TimedBaseModel):
    id: int
    team_id: int
    name: str
    description: Optional[str] = None
    type: str
    payload: Optional[dict] = None


class TelemetryScoreEntity(BaseModel):
    item_id: int
    team_id: int
    project_id: int
    user_id: str
    user_role: str
    score_id: int
    value: Optional[Any] = None
    weight: Optional[float] = None


class ScoreEntity(TimedBaseModel):
    id: int
    name: str
    value: Optional[Any] = None
    weight: Optional[float] = None


class ScorePayloadEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_id: str
    value: Any
    weight: Optional[Union[float, int]] = 1.0

    @field_validator("weight", mode="before")
    @classmethod
    def validate_weight(cls, v):
        if v is not None and (not isinstance(v, (int, float)) or v <= 0):
            raise AppException("Please provide a valid number greater than 0")
        return v

    @model_validator(mode="after")
    def check_weight_and_value(self):
        value = self.value
        weight = self.weight
        if (weight is None and value is not None) or (
            weight is not None and value is None
        ):
            raise AppException("Weight and Value must both be set or both be None.")
        return self
