from enum import Enum
from typing import List
from typing import Optional
from typing import Union

from lib.core.entities.utils import Attribute
from lib.core.entities.utils import BaseInstance
from lib.core.entities.utils import BaseModel
from lib.core.entities.utils import BboxPoints
from lib.core.entities.utils import INVALID_DICT_MESSAGE
from lib.core.entities.utils import MetadataBase
from lib.core.entities.utils import NotEmptyStr
from lib.core.entities.utils import PointLabels
from lib.core.entities.utils import Tag
from pydantic import conlist
from pydantic import Field
from pydantic import StrictBool
from pydantic import StrictInt
from pydantic import ValidationError
from pydantic.error_wrappers import ErrorWrapper


class VideoType(str, Enum):
    EVENT = "event"
    BBOX = "bbox"


class MetaData(MetadataBase):
    duration: Optional[StrictInt]
    error: Optional[StrictBool]


class BaseTimeStamp(BaseModel):
    timestamp: StrictInt
    attributes: Optional[List[Attribute]] = Field(list())


class BboxTimeStamp(BaseTimeStamp):
    points: BboxPoints


class EventTimeStamp(BaseTimeStamp):
    pass


class InstanceMetadata(BaseInstance):
    type: VideoType
    class_name: Optional[NotEmptyStr] = Field(None, alias="className")
    start: StrictInt
    end: StrictInt

    class Config:
        fields = {"creation_type": {"exclude": True}}


class BBoxInstanceMetadata(InstanceMetadata):
    type: VideoType = Field(VideoType.BBOX.value, const=True)
    point_labels: Optional[PointLabels] = Field(None, alias="pointLabels")


class EventInstanceMetadata(InstanceMetadata):
    type: VideoType = Field(VideoType.EVENT.value, const=True)


class BaseParameter(BaseModel):
    start: StrictInt
    end: StrictInt


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
            loc = []
            try:
                loc = ["meta"]
                meta_data = values["meta"]
                loc.append("type")
                instance_type = meta_data["type"]
            except KeyError:
                raise ValidationError(
                    [ErrorWrapper(ValueError("field required"), ".".join(loc))], cls
                )
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
        except TypeError as e:
            raise ValidationError(
                [ErrorWrapper(ValueError(INVALID_DICT_MESSAGE), "meta",)], cls,
            )


class VideoAnnotation(BaseModel):
    metadata: MetaData
    instances: Optional[List[VideoInstance]] = Field(list())
    tags: Optional[List[Tag]] = Field(list())
