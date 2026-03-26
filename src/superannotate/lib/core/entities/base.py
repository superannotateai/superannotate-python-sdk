import re
from datetime import datetime
from typing import Annotated
from typing import Literal
from typing import Optional
from typing import Union

from lib.core import BACKEND_URL
from lib.core import LOG_FILE_LOCATION
from pydantic import AfterValidator
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import PlainSerializer
from pydantic_extra_types.color import Color

DATE_TIME_FORMAT_ERROR_MESSAGE = (
    "does not match expected format YYYY-MM-DDTHH:MM:SS.fffZ"
)
DATE_REGEX = r"\d{4}-[01]\d-[0-3]\dT[0-2]\d:[0-5]\d:[0-5]\d(?:\.\d{3})Z"

_missing = object()


def _validate_hex_color(v: str) -> str:
    """Convert color to hex format."""
    color = Color(v)
    return "#{:02X}{:02X}{:02X}".format(*color.as_rgb_tuple()[:3])


HexColor = Annotated[str, AfterValidator(_validate_hex_color)]


def _validate_string_date(v: Union[datetime, str]) -> str:
    """Convert datetime to string format."""
    if isinstance(v, str):
        return v
    return v.isoformat().split("+")[0] + ".000Z"


def _serialize_string_date(v: Union[datetime, str]) -> str:
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

    id: Optional[int] = None
    name: str


class TimedBaseModel(BaseModel):
    createdAt: Optional[StringDate] = Field(
        None, alias="createdAt", description="Date of creation"
    )
    updatedAt: Optional[StringDate] = Field(
        None, alias="updatedAt", description="Update date"
    )


class BaseItemEntity(TimedBaseModel):
    model_config = ConfigDict(extra="allow")

    id: Optional[int] = None
    name: Optional[str] = None
    folder_id: Optional[int] = None
    path: Optional[str] = Field(
        None, description="Item’s path in SuperAnnotate project"
    )
    url: Optional[str] = Field(None, description="Publicly available HTTP address")
    annotator_email: Optional[str] = Field(None, description="Annotator email")
    qa_email: Optional[str] = Field(None, description="QA email")
    annotation_status: Optional[Union[int, str]] = Field(
        None, description="Item annotation status"
    )
    entropy_value: Optional[float] = Field(
        None, description="Priority score of given item"
    )
    custom_metadata: Optional[dict] = None
    assignments: Optional[list] = Field(default_factory=list)

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


TOKEN_PATTERN = re.compile(r"^[-.@_A-Za-z0-9]+=\d+$")


def _validate_token(value: str) -> str:
    """Validate token format."""
    if not TOKEN_PATTERN.match(value):
        raise ValueError("Invalid token.")
    return value


# Pydantic v2 compatible TokenStr using Annotated
TokenStr = Annotated[str, AfterValidator(_validate_token)]


class ConfigEntity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    API_TOKEN: TokenStr = Field(alias="SA_TOKEN")
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
