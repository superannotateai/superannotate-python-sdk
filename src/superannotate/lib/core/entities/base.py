import re
from datetime import datetime
from typing import Optional
from typing import Union

from lib.core import BACKEND_URL
from lib.core import LOG_FILE_LOCATION
from lib.core.pydantic_v1 import BaseModel
from lib.core.pydantic_v1 import Extra
from lib.core.pydantic_v1 import Field
from lib.core.pydantic_v1 import Literal
from lib.core.pydantic_v1 import parse_datetime
from lib.core.pydantic_v1 import StrictStr

DATE_TIME_FORMAT_ERROR_MESSAGE = (
    "does not match expected format YYYY-MM-DDTHH:MM:SS.fffZ"
)
DATE_REGEX = r"\d{4}-[01]\d-[0-3]\dT[0-2]\d:[0-5]\d:[0-5]\d(?:\.\d{3})Z"

try:
    from pydantic import AbstractSetIntStr  # noqa
    from pydantic import MappingIntStrAny  # noqa
except ImportError:
    pass
_missing = object()


class StringDate(datetime):
    @classmethod
    def __get_validators__(cls):
        yield parse_datetime
        yield cls.validate

    @classmethod
    def validate(cls, v: datetime):
        v = v.isoformat().split("+")[0] + ".000Z"
        return v


class SubSetEntity(BaseModel):
    id: Optional[int]
    name: str

    class Config:
        extra = Extra.ignore


class TimedBaseModel(BaseModel):
    createdAt: Optional[StringDate] = Field(
        None, alias="createdAt", description="Date of creation"
    )
    updatedAt: Optional[StringDate] = Field(
        None, alias="updatedAt", description="Update date"
    )


class BaseItemEntity(TimedBaseModel):
    id: Optional[int]
    name: Optional[str]
    folder_id: Optional[int]
    path: Optional[str] = Field(
        None, description="Item’s path in SuperAnnotate project"
    )
    url: Optional[str] = Field(description="Publicly available HTTP address")
    annotator_email: Optional[str] = Field(None, description="Annotator email")
    qa_email: Optional[str] = Field(None, description="QA email")
    annotation_status: Optional[Union[int, str]] = Field(
        None, description="Item annotation status"
    )
    entropy_value: Optional[float] = Field(description="Priority score of given item")
    custom_metadata: Optional[dict]
    assignments: Optional[list] = Field([])

    class Config:
        extra = Extra.allow

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


class TokenStr(StrictStr):
    regex = r"^[-.@_A-Za-z0-9]+=\d+$"

    @classmethod
    def validate(cls, value: Union[str]) -> Union[str]:
        if cls.curtail_length and len(value) > cls.curtail_length:
            value = value[: cls.curtail_length]
        if cls.regex:
            if not re.match(cls.regex, value):
                raise ValueError("Invalid token.")
        return value


class ConfigEntity(BaseModel):
    API_TOKEN: TokenStr = Field(alias="SA_TOKEN")
    API_URL: str = Field(alias="SA_URL", default=BACKEND_URL)
    LOGGING_LEVEL: Literal[
        "NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
    ] = "INFO"
    LOGGING_PATH: str = f"{LOG_FILE_LOCATION}"
    VERIFY_SSL: bool = True
    ANNOTATION_CHUNK_SIZE = 5000
    ITEM_CHUNK_SIZE = 2000
    MAX_THREAD_COUNT = 4
    MAX_COROUTINE_COUNT = 8

    class Config:
        extra = Extra.ignore
