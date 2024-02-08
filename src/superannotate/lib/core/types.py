from typing import Optional

from lib.core.pydantic_v1 import BaseModel
from lib.core.pydantic_v1 import constr
from lib.core.pydantic_v1 import Extra

NotEmptyStr = constr(strict=True, min_length=1)


class Project(BaseModel):
    name: NotEmptyStr

    class Config:
        extra = Extra.allow


class MLModel(BaseModel):
    name: NotEmptyStr
    id: Optional[int]
    path: NotEmptyStr
    config_path: NotEmptyStr
    team_id: Optional[int]

    class Config:
        extra = Extra.allow


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
