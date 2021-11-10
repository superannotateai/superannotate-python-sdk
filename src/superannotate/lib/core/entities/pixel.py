from typing import List
from typing import Optional

from lib.core.entities.utils import BaseImageInstance
from lib.core.entities.utils import BaseModel
from lib.core.entities.utils import MetadataBase
from lib.core.entities.utils import PixelColor
from lib.core.entities.utils import Tag
from pydantic import Field


class PixelMetaData(MetadataBase):
    is_segmented: Optional[bool] = Field(None, alias="isSegmented")


class PixelAnnotationPart(BaseModel):
    color: PixelColor


class PixelAnnotationInstance(BaseImageInstance):
    parts: List[PixelAnnotationPart]


class PixelAnnotation(BaseModel):
    metadata: PixelMetaData
    instances: List[PixelAnnotationInstance]
    tags: Optional[List[Tag]] = Field(list())