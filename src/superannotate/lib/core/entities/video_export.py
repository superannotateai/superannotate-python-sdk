from enum import Enum
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from lib.core.entities.utils import Attribute
from lib.core.entities.utils import BaseInstance
from lib.core.entities.utils import BaseModel
from lib.core.entities.utils import BboxPoints
from lib.core.entities.utils import MetadataBase
from lib.core.entities.utils import NotEmptyStr
from lib.core.entities.utils import PointLabels
from lib.core.entities.utils import Tag
from pydantic import conlist
from pydantic import Field
from pydantic import ValidationError
from pydantic.error_wrappers import ErrorWrapper


class VideoType(str, Enum):
    EVENT = "event"
    BBOX = "bbox"


class MetaData(MetadataBase):
    duration: Optional[int]
    error: Optional[bool]


class BaseTimeStamp(BaseModel):
    timestamp: int
    attributes: List[Attribute]


class BboxTimeStamp(BaseTimeStamp):
    points: BboxPoints


class EventTimeStamp(BaseTimeStamp):
    pass


class InstanceMetadata(BaseInstance):
    type: VideoType
    class_name: Optional[NotEmptyStr] = Field(None, alias="className")
    point_labels: Optional[PointLabels] = Field(None, alias="pointLabels")
    start: int
    end: int

    class Config:
        fields = {"creation_type": {"exclude": True}}


class BBoxInstanceMetadata(InstanceMetadata):
    type: VideoType = Field(VideoType.BBOX.value, const=True)


class EventInstanceMetadata(InstanceMetadata):
    type: VideoType = Field(VideoType.EVENT.value, const=True)


class BaseParameter(BaseModel):
    start: int
    end: int


class BboxParameter(BaseParameter):
    timestamps: conlist(BboxTimeStamp, min_items=1)


class EventParameter(BaseParameter):
    timestamps: conlist(EventTimeStamp, min_items=1)


class BboxInstance(BaseModel):
    meta: BBoxInstanceMetadata
    parameters: conlist(BboxParameter, min_items=1)


class EventInstance(BaseModel):
    meta: EventInstanceMetadata
    parameters: conlist(EventParameter, min_items=1)


INSTANCES = {VideoType.BBOX.value: BboxInstance, VideoType.EVENT.value: EventInstance}


class VideoInstance(BaseModel):
    __root__: Union[BboxInstance, EventInstance]

    @classmethod
    def __get_validators__(cls):
        yield cls.return_action

    @classmethod
    def return_action(cls, values):
        try:
            instance_type = values["meta"]["type"]
        except KeyError:
            raise ValidationError(
                [ErrorWrapper(ValueError("meta.field required"), "type")], cls
            )
        try:
            return INSTANCES[instance_type](**values)
        except KeyError:
            raise ValidationError(
                [
                    ErrorWrapper(
                        ValueError(
                            f"invalid type, valid types are {', '.join(INSTANCES.keys())}"
                        ),
                        "meta.type",
                    )
                ],
                cls,
            )


class VideoAnnotation(BaseModel):
    metadata: MetaData
    instances: Optional[List[VideoInstance]] = Field(list())
    tags: Optional[List[Tag]] = Field(list())
