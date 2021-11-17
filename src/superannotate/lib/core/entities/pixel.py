from typing import List
from typing import Optional

from lib.core.entities.utils import BaseImageInstance
from lib.core.entities.utils import BaseModel
from lib.core.entities.utils import Comment
from lib.core.entities.utils import Metadata
from lib.core.entities.utils import Tag
from pydantic import Field
from pydantic import StrictBool
from pydantic import validator
from pydantic.color import Color
from pydantic.color import ColorType


class PixelMetaData(Metadata):
    is_segmented: Optional[StrictBool] = Field(None, alias="isSegmented")


class PixelAnnotationPart(BaseModel):
    color: ColorType

    @validator("color")
    def validate_color(cls, v):
        color = Color(v)
        return color.as_hex()


class PixelAnnotationInstance(BaseImageInstance):
    parts: List[PixelAnnotationPart]


class PixelAnnotation(BaseModel):
    metadata: PixelMetaData
    instances: List[PixelAnnotationInstance] = Field(list())
    tags: Optional[List[Tag]] = Field(list())
    comments: Optional[List[Comment]] = Field(list())
