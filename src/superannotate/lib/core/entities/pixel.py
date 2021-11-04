from typing import List
from typing import Optional

from utils import Attribute
from utils import Metadata
from utils import NotEmptyStr

from pydantic import BaseModel
from pydantic import Field


class PixelAnnotationPart(BaseModel):
    color: NotEmptyStr


class PixelAnnotationInstance(BaseModel):
    class_id: Optional[int] = Field(None, alias="classId")
    group_id: Optional[int] = Field(None, alias="groupId")
    parts: List[PixelAnnotationPart]
    attributes: List[Attribute]


class PixelAnnotation(BaseModel):
    metadata: Metadata
    instances: List[PixelAnnotationInstance]
