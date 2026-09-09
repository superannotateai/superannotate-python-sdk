import re
from datetime import datetime
from typing import Annotated
from typing import Literal

from lib.core import BACKEND_URL
from lib.core import INVALID_TOKEN_ERROR
from lib.core import LOG_FILE_LOCATION
from pydantic import AfterValidator
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import PlainSerializer
from pydantic_extra_types.color import Color

_missing = object()


def _validate_hex_color(v: str) -> str:
    """Convert color to hex format."""
    color = Color(v)
    return "#{:02X}{:02X}{:02X}".format(*color.as_rgb_tuple()[:3])


HexColor = Annotated[str, AfterValidator(_validate_hex_color)]


def _validate_string_date(v: datetime | str) -> str:
    """Convert datetime to string format."""
    if isinstance(v, str):
        return v
    return v.isoformat().split("+")[0] + ".000Z"


def _serialize_string_date(v: datetime | str) -> str:
    """Serialize datetime or string to string format. For case data input."""
    if isinstance(v, str):
        return v
    if isinstance(v, datetime):
        return v.isoformat().split("+")[0] + ".000Z"
    return v


StringDate = Annotated[
    datetime,
    AfterValidator(_validate_string_date),
    PlainSerializer(_serialize_string_date, return_type=str),
]


class SubSetEntity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int | None = None
    name: str


class TimedBaseModel(BaseModel):
    createdAt: StringDate | None = Field(
        None, alias="createdAt", description="Date of creation"
    )
    updatedAt: StringDate | None = Field(
        None, alias="updatedAt", description="Update date"
    )


class BaseItemEntity(TimedBaseModel):
    model_config = ConfigDict(extra="allow")

    id: int | None = None
    name: str | None = None
    folder_id: int | None = None
    path: str | None = Field(None, description="Item’s path in SuperAnnotate project")
    url: str | None = Field(None, description="Publicly available HTTP address")
    annotator_email: str | None = Field(None, description="Annotator email")
    qa_email: str | None = Field(None, description="QA email")
    annotation_status: int | str | None = Field(
        None, description="Item annotation status"
    )
    entropy_value: float | None = Field(
        None, description="Priority score of given item"
    )
    custom_metadata: dict | None = None
    assignments: list | None = Field(default_factory=list)

    def __hash__(self):
        return hash(self.name)

    def add_path(self, project_name: str, folder_name: str):
        self.path = (
            f"{project_name}{f'/{folder_name}' if folder_name != 'root' else ''}"
        )
        return self

    @staticmethod
    def map_fields(entity: dict) -> dict:
        if "metadata" in entity:
            entity["url"] = entity["metadata"]["path"]
        else:
            entity["url"] = entity["path"]
        entity["path"] = None
        return entity


#: Legacy team-owner token: ``<name>=<team_id>`` — the team is part of the token.
TOKEN_PATTERN = re.compile(r"^[-.@_A-Za-z0-9]+=\d+$")
#: New-style API key (team / team-user / organization scoped). Its scope is not in the
#: token, it is resolved via the work-management ``users/me`` endpoint. Matched by shape
#: rather than by the ``sa_`` prefix so future prefixes keep working; the length bound
#: keeps malformed input ("INVALID_TOKEN") reported as an invalid token instead of
#: being sent to the backend.
API_KEY_PATTERN = re.compile(r"^[-_A-Za-z0-9]{32,}$")


def is_legacy_token(value: str) -> bool:
    """Whether the token carries its team id, as opposed to being a scoped API key."""
    return bool(TOKEN_PATTERN.match(value))


def _validate_token(value: str) -> str:
    """Validate token format."""
    if not is_legacy_token(value) and not API_KEY_PATTERN.match(value):
        raise ValueError(INVALID_TOKEN_ERROR)
    return value


# Pydantic v2 compatible TokenStr using Annotated
TokenStr = Annotated[str, AfterValidator(_validate_token)]


class ConfigEntity(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    API_TOKEN: TokenStr = Field(alias="SA_TOKEN")
    #: The team to operate in. Only an organization API key needs it — its scope carries
    #: no team; every other token resolves its own team.
    TEAM_ID: int | None = Field(alias="SA_TEAM_ID", default=None)
    API_URL: str = Field(alias="SA_URL", default=BACKEND_URL)
    LOGGING_LEVEL: Literal[
        "NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
    ] = "INFO"
    LOGGING_PATH: str = f"{LOG_FILE_LOCATION}"
    VERIFY_SSL: bool = True
    ANNOTATION_CHUNK_SIZE: int = 5000
    ITEM_CHUNK_SIZE: int = 2000
    MAX_THREAD_COUNT: int = 4
    MAX_COROUTINE_COUNT: int = 8
