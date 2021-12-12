from enum import Enum
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from lib.core.entities.utils import Attribute
from lib.core.entities.utils import BaseInstance
from lib.core.entities.utils import BboxPoints
from lib.core.entities.utils import MetadataBase
from lib.core.entities.utils import NotEmptyStr
from lib.core.entities.utils import Tag
from pydantic import BaseModel
from pydantic import constr
from pydantic import Field
from pydantic import StrictBool
from pydantic import StrictInt
from pydantic import StrictStr


class VideoType(str, Enum):
    EVENT = "event"
    BBOX = "bbox"


class MetaData(MetadataBase):
    name: Optional[StrictStr]
    width: Optional[StrictInt]
    height: Optional[StrictInt]
    duration: Optional[StrictInt]


class BaseTimeStamp(BaseModel):
    active: Optional[StrictBool]
    attributes: Optional[Dict[constr(regex=r"^[-|+]$"), List[Attribute]]]  # noqa: F722


class BboxTimeStamp(BaseTimeStamp):
    points: Optional[BboxPoints]


class BaseVideoInstance(BaseInstance):
    id: Optional[str]
    type: VideoType
    locked: Optional[StrictBool]
    timeline: Dict[float, BaseTimeStamp]


class BboxInstance(BaseVideoInstance):
    point_labels: Optional[
        Dict[constr(regex=r"^[0-9]+$"), NotEmptyStr]
    ] = Field(  # noqa F722
        None, alias="pointLabels"
    )
    timeline: Dict[float, BboxTimeStamp]


class EventInstance(BaseVideoInstance):
    pass


class VideoAnnotation(BaseModel):
    metadata: MetaData
    instances: Optional[List[Union[EventInstance, BboxInstance]]] = Field(list())
    tags: Optional[List[Tag]] = Field(list())
