import re
from datetime import datetime
from typing import Annotated
from typing import Any
from typing import Literal
from typing import Optional
from typing import Union

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic.functional_validators import BeforeValidator

from lib.core import BACKEND_URL
from lib.core import LOG_FILE_LOCATION

DATE_TIME_FORMAT_ERROR_MESSAGE = (
    "does not match expected format YYYY-MM-DDTHH:MM:SS.fffZ"
)
DATE_REGEX = r"\d{4}-[01]\d-[0-3]\dT[0-2]\d:[0-5]\d:[0-5]\d(?:\.\d{3})Z"

_missing = object()


def _parse_string_date(v: Any) -> Optional[str]:
    """Parse datetime to string format."""
    if v is None:
        return None
    if isinstance(v, str):
        return v
    if isinstance(v, datetime):
        return v.isoformat().split("+")[0] + ".000Z"
    # Try to parse as datetime
    try:
        from dateutil.parser import parse

        dt = parse(str(v))
        return dt.isoformat().split("+")[0] + ".000Z"
    except Exception:
        return str(v)


# StringDate as Annotated type with BeforeValidator
StringDate = Annotated[Optional[str], BeforeValidator(_parse_string_date)]


class SubSetEntity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Optional[int] = None
    name: str


class TimedBaseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    createdAt: StringDate = Field(
        default=None, alias="createdAt", description="Date of creation"
    )
    updatedAt: StringDate = Field(
        default=None, alias="updatedAt", description="Update date"
    )


class BaseItemEntity(TimedBaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: Optional[int] = None
    name: Optional[str] = None
    folder_id: Optional[int] = None
    path: Optional[str] = Field(
        default=None, description="Item’s path in SuperAnnotate project"
    )
    url: Optional[str] = Field(
        default=None, description="Publicly available HTTP address"
    )
    annotator_email: Optional[str] = Field(default=None, description="Annotator email")
    qa_email: Optional[str] = Field(default=None, description="QA email")
    annotation_status: Optional[Union[int, str]] = Field(
        default=None, description="Item annotation status"
    )
    entropy_value: Optional[float] = Field(
        default=None, description="Priority score of given item"
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


def _validate_token(value: str) -> str:
    """Validate token string format."""
    token_regex = r"^[-.@_A-Za-z0-9]+=\d+$"
    if not re.match(token_regex, value):
        raise ValueError("Invalid token.")
    return value


# TokenStr as Annotated type for Pydantic v2 compatibility
TokenStr = Annotated[str, BeforeValidator(_validate_token)]


class ConfigEntity(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

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
