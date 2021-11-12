from typing import List
from typing import Optional
from typing import Union

from lib.core.entities.utils import BaseModel
from lib.core.entities.utils import BaseVectorInstance
from lib.core.entities.utils import BboxPoints
from lib.core.entities.utils import Comment
from lib.core.entities.utils import Metadata
from lib.core.entities.utils import NotEmptyStr
from lib.core.entities.utils import Tag
from lib.core.entities.utils import VectorAnnotationTypeEnum
from pydantic import conlist
from pydantic import Field


class AxisPoint(BaseModel):
    x: float
    y: float


class Point(BaseVectorInstance, AxisPoint):
    pass


class PolyLine(BaseVectorInstance):
    points: List[float]


class Polygon(BaseVectorInstance):
    points: List[float]


class Bbox(BaseVectorInstance):
    points: BboxPoints


class RotatedBoxPoints(BaseVectorInstance):
    x1: float
    y1: float
    x2: float
    y2: float
    x3: float
    y3: float
    x4: float
    y4: float


class RotatedBox(BaseVectorInstance):
    points: RotatedBoxPoints


class Ellipse(BaseVectorInstance):
    cx: float
    cy: float
    rx: float
    ry: float
    angle: float


class TemplatePoint(BaseModel):
    id: int
    x: float
    y: float


class TemplateConnection(BaseModel):
    id: int
    from_connection: int = Field(alias="from")
    to_connection: int = Field(alias="to")


class Template(BaseVectorInstance):
    points: conlist(TemplatePoint, min_items=1)
    connections: List[TemplateConnection]
    template_id: Optional[int] = Field(None, alias="templateId")
    template_name: NotEmptyStr = Field(alias="templateName")


class CuboidPoint(BaseModel):
    f1: AxisPoint
    f2: AxisPoint
    r1: AxisPoint
    r2: AxisPoint


class Cuboid(BaseVectorInstance):
    points: CuboidPoint


ANNOTATION_TYPES = {
    VectorAnnotationTypeEnum.BBOX: Bbox,
    VectorAnnotationTypeEnum.TEMPLATE: Template,
    VectorAnnotationTypeEnum.CUBOID: Cuboid,
    VectorAnnotationTypeEnum.POLYGON: Polygon,
    VectorAnnotationTypeEnum.POINT: Point,
    VectorAnnotationTypeEnum.POLYLINE: PolyLine,
    VectorAnnotationTypeEnum.ELLIPSE: Ellipse,
    VectorAnnotationTypeEnum.RBBOX: RotatedBox,
}


class AnnotationInstance(BaseModel):
    __root__: Union[
        Template, Cuboid, Point, PolyLine, Polygon, Bbox, Ellipse, RotatedBox
    ]

    @classmethod
    def __get_validators__(cls):
        yield cls.return_action

    @classmethod
    def return_action(cls, values):
        try:
            instance_type = values["type"]
        except KeyError:
            raise ValueError("metadata.type required")
        try:
            return ANNOTATION_TYPES[instance_type](**values)
        except KeyError:
            raise ValueError(
                f"invalid type, valid types is {', '.join(ANNOTATION_TYPES.keys())}"
            )


class VectorAnnotation(BaseModel):
    metadata: Metadata
    comments: Optional[List[Comment]] = Field(list())
    tags: Optional[List[Tag]] = Field(list())
    instances: Optional[List[AnnotationInstance]] = Field(list())
