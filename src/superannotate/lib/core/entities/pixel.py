from typing import List

from lib.core.entities.utils import BaseImageInstance
from lib.core.entities.utils import Metadata
from lib.core.entities.utils import NotEmptyStr
from pydantic import BaseModel


class PixelAnnotationPart(BaseModel):
    color: NotEmptyStr  # TODO hex validation


class PixelAnnotationInstance(BaseImageInstance):
    parts: List[PixelAnnotationPart]


class PixelAnnotation(BaseModel):
    metadata: Metadata
    instances: List[PixelAnnotationInstance]
