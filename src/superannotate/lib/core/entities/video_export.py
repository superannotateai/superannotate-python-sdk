from enum import Enum
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from lib.core.entities.utils import AnnotationStatusEnum
from lib.core.entities.utils import Attribute
from lib.core.entities.utils import BaseInstance
from lib.core.entities.utils import BboxPoints
from lib.core.entities.utils import MetadataBase
from lib.core.entities.utils import NotEmptyStr
from lib.core.entities.utils import PointLabels
from lib.core.entities.utils import Tag
from pydantic import BaseModel
from pydantic import Field


class VideoType(str, Enum):
    EVENT = "event"
    BBOX = "bbox"


class MetaData(MetadataBase):
    name: NotEmptyStr
    url: str
    status: Optional[AnnotationStatusEnum]
    duration: Optional[int]
    error: Optional[bool]


class BaseTimeStamp(BaseModel):
    timestamp: int
    attributes: List[Attribute]


class BboxTimeStamp(BaseTimeStamp):
    points: Optional[BboxPoints]


class EventTimeStamp(BaseTimeStamp):
    pass


class InstanceMetadata(BaseInstance):
    type: VideoType
    class_name: str = Field(alias="className")
    point_labels: Optional[PointLabels] = Field(None, alias="pointLabels")
    start: int
    end: int

    class Config:
        fields = {'creation_type': {'exclude': True}}


class BaseVideoInstance(BaseModel):
    metadata: InstanceMetadata
    id: Optional[str]
    type: VideoType
    locked: Optional[bool]
    timeline: Dict[float, BaseTimeStamp]


class BaseParameter(BaseModel):
    start: int
    end: int


class BboxParameter(BaseParameter):
    timestamps: List[BboxTimeStamp]


class EventParameter(BaseParameter):
    timestamps: List[EventTimeStamp]


class BboxInstance(BaseModel):
    metadata: InstanceMetadata
    parameters: List[BboxParameter]


class EventInstance(BaseModel):
    metadata: InstanceMetadata
    parameters: List[EventParameter]


class VideoAnnotation(BaseModel):
    metadata: MetaData
    instances: List[Union[EventInstance, BboxInstance]]
    tags: List[Tag]