from typing import List

from lib.core.entities.utils import BaseImageInstance
from lib.core.entities.utils import hex_color
from lib.core.entities.utils import Metadata
from pydantic import BaseModel


class PixelAnnotationPart(BaseModel):
    color: hex_color


class PixelAnnotationInstance(BaseImageInstance):
    parts: List[PixelAnnotationPart]


class PixelAnnotation(BaseModel):
    metadata: Metadata
    instances: List[PixelAnnotationInstance]
