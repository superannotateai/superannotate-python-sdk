from typing import List
from typing import Optional

from lib.core.entities.utils import BaseImageInstance
from lib.core.entities.utils import hex_color
from lib.core.entities.utils import Metadata
from pydantic import BaseModel
from pydantic import Field


class PixelMetaData(Metadata):
    is_segmented: Optional[bool] = Field(None, alias="isSegmented")


class PixelAnnotationPart(BaseModel):
    color: hex_color


class PixelAnnotationInstance(BaseImageInstance):
    parts: List[PixelAnnotationPart]


class PixelAnnotation(BaseModel):
    metadata: PixelMetaData
    instances: List[PixelAnnotationInstance]
