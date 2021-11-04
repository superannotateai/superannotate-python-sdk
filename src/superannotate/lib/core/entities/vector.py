from typing import List
from typing import Optional
from typing import Union

from pydantic import BaseModel
from pydantic import Field
from pydantic import StrictStr
from pydantic import validate_model
from pydantic import ValidationError
from pydantic import validator
from utils import AttributeGroup
from utils import BaseImageInstance
from utils import BboxPoints
from utils import Comment
from utils import Metadata
from utils import VectorAnnotationType
from utils import Tag


class ClassesJson(BaseModel):
    name: StrictStr
    color: StrictStr
    attribute_groups: List[AttributeGroup]


# todo fill
class Tags(BaseModel):
    items: Optional[List[str]]


class Point(BaseImageInstance):
    x: float
    y: float


class PolyLine(BaseImageInstance):
    points: List[float]


class Polygon(BaseImageInstance):
    points: List[float]


class Bbox(BaseImageInstance):
    points: BboxPoints


class Ellipse(BaseImageInstance):
    cx: float
    cy: float
    rx: float
    ry: float


class TemplatePoint(BaseModel):
    id: int
    x: float
    y: float


class TemplateConnection(BaseModel):
    id: int
    to: int


class Template(BaseImageInstance):
    points: List[TemplatePoint]
    connections: List[Optional[TemplateConnection]]
    template_id: int = Field(alias="templateId")


class CuboidPoint(BaseModel):
    f1: Point
    f2: Point
    r1: Point
    r2: Point


class Cuboid(BaseImageInstance):
    points: CuboidPoint


ANNOTATION_TYPES = {
    VectorAnnotationType.BBOX: Bbox,
    VectorAnnotationType.TEMPLATE: Template,
    VectorAnnotationType.CUBOID: Cuboid,
    VectorAnnotationType.POLYGON: Polygon,
    VectorAnnotationType.POINT: Point,
    VectorAnnotationType.POLYLINE: PolyLine,
    VectorAnnotationType.ELLIPSE: Ellipse
}


class VectorAnnotation(BaseModel):
    metadata: Metadata
    comments: List[Comment]
    tags: Optional[List[Tag]]
    instances: Optional[List[Union[Template, Cuboid, Point, PolyLine, Polygon, Bbox, Ellipse]]]

    @validator("instances", pre=True, each_item=True)
    def check_instances(cls, instance):
        # todo add type checking
        annotation_type = instance.get("type")
        result = validate_model(ANNOTATION_TYPES[annotation_type], instance)
        if result[2]:
            raise ValidationError(result[2].raw_errors, model=ANNOTATION_TYPES[annotation_type])
        return instance
