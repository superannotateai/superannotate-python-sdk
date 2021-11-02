from typing import List
from typing import Optional

from pydantic import BaseModel
from src.superannotate.lib.core.entites.utils import Attribute
from src.superannotate.lib.core.entites.utils import Metadata
from src.superannotate.lib.core.entites.utils import NotEmptyStr


class PixelAnnotationPart(BaseModel):
    color: NotEmptyStr


class PixelAnnotationInstance(BaseModel):
    classId: Optional[int]
    groupId: Optional[int]
    parts: List[PixelAnnotationPart]
    attributes: List[Attribute]


class PixelAnnotation(BaseModel):
    metadata: Metadata
    instances: List[PixelAnnotationInstance]
