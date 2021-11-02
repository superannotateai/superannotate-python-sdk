from enum import Enum
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from pydantic import BaseModel
from pydantic import constr
from pydantic import EmailStr
from pydantic import Field
from pydantic import StrictStr
from src.superannotate.lib.core.entites.utils import BboxPoints
from src.superannotate.lib.core.entites.utils import PointLabels
from src.superannotate.lib.core.entites.utils import TimedBaseModel
from src.superannotate.lib.core.entites.utils import TrackableBaseModel


class VideoType(str, Enum):
    EVENT = "event"
    BBOX = "bbox"


class LastUserAction(BaseModel):
    email: EmailStr
    # TODO change to timestamp
    timestamp: float


class VideoMetaData(BaseModel):
    name: StrictStr
    width: Optional[int]
    height: Optional[int]
    duration: Optional[int]
    last_action: Optional[LastUserAction] = Field(None, alias="lastAction")


class TimeStampAttribute(BaseModel):
    id: int
    group_id: int = Field(None, alias="groupId")


class BaseTimeStamp(BaseModel):
    active: Optional[bool]
    attributes: Optional[Dict[constr(regex=r"^[-|+]$"), List[TimeStampAttribute]]]


class BboxTimeStamp(BaseTimeStamp):
    points: Optional[BboxPoints]


class BaseVideoInstance(TimedBaseModel, TrackableBaseModel):
    id: Optional[str]
    type: VideoType
    class_id: int = Field(None, alias="classId")
    locked: Optional[bool]
    pointLabels: Optional[PointLabels]
    timeline: Dict[float, BaseTimeStamp]


class BboxInstance(BaseVideoInstance):
    pointLabels: Optional[PointLabels]
    timeline: Dict[float, BboxTimeStamp]


class EventInstance(BaseVideoInstance):
    pass


class VideoAnnotation(BaseModel):
    metadata: VideoMetaData
    instances: Optional[List[Union[EventInstance, BboxInstance]]]
    tags: Optional[List[str]]
