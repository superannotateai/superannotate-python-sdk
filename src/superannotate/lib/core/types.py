from typing import Annotated

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import StringConstraints

NotEmptyStr = Annotated[str, StringConstraints(strict=True, min_length=1)]


class Project(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: NotEmptyStr


class PriorityScoreEntity(BaseModel):
    name: NotEmptyStr
    priority: float


class Attachment(BaseModel):
    name: str
    path: str
    integration_id: int | None = None


class AttachmentMeta(BaseModel):
    width: float | None = None
    height: float | None = None
    integration_id: int | None = None
