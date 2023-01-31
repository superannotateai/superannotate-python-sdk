from typing import Optional

from pydantic import BaseModel
from pydantic import constr
from pydantic import Extra

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


class AttachmentMeta(BaseModel):
    width: Optional[float] = None
    height: Optional[float] = None
