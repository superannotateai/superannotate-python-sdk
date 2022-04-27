from typing import Optional

from pydantic import BaseModel
from pydantic import constr
from pydantic import Extra
from superannotate_schemas.schemas.classes import AttributeGroup as AttributeGroupSchema

NotEmptyStr = constr(strict=True, min_length=1)

AttributeGroup = AttributeGroupSchema


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


class PriorityScore(BaseModel):
    name: NotEmptyStr
    priority: float
