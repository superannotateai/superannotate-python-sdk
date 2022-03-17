from typing import Optional
from typing import Union

from pydantic import BaseModel
from pydantic import constr
from pydantic import Extra
from pydantic import StrictStr
from pydantic.error_wrappers import ErrorWrapper
from pydantic.error_wrappers import ValidationError
from superannotate_schemas.schemas.classes import AttributeGroup as AttributeGroupSchema

NotEmptyStr = constr(strict=True, min_length=1)

AttributeGroup = AttributeGroupSchema


class AnnotationType(StrictStr):
    @classmethod
    def validate(cls, value: str) -> Union[str]:
        if value not in ANNOTATION_TYPES.keys():
            raise ValidationError(
                [ErrorWrapper(TypeError(f"invalid value {value}"), "type")], cls
            )
        return value


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
