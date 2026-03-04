from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import StringConstraints
from typing_extensions import Annotated

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
    integration_id: Optional[int] = None


class AttachmentMeta(BaseModel):
    width: Optional[float] = None
    height: Optional[float] = None
    integration_id: Optional[int] = None
