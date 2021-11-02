from typing import List
from typing import Optional
from typing import Union

from pydantic import BaseModel
from pydantic import Field
from pydantic import StrictStr
from pydantic import validate_model
from pydantic import ValidationError
from pydantic import validator
from src.superannotate.lib.core.entites.utils import AttributeGroup
from src.superannotate.lib.core.entites.utils import BaseInstance
from src.superannotate.lib.core.entites.utils import BboxPoints
from src.superannotate.lib.core.entites.utils import Comment
from src.superannotate.lib.core.entites.utils import Metadata
from src.superannotate.lib.core.entites.utils import VectorAnnotationType


class ClassesJson(BaseModel):
    name: StrictStr
    color: StrictStr
    attribute_groups: List[AttributeGroup]


# todo fill
class Tags(BaseModel):
    items: Optional[List[str]]


class Point(BaseInstance):
    x: float
    y: float


class PolyLine(BaseInstance):
    points: List[float]


class Polygon(BaseInstance):
    points: List[float]


class Bbox(BaseInstance):
    points: BboxPoints


class Ellipse(BaseInstance):
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


class Template(BaseInstance):
    points: List[TemplatePoint]
    connections: List[Optional[TemplateConnection]]
    template_id: int = Field(None, alias="templateId")


class CuboidPoint(BaseModel):
    f1: Point
    f2: Point
    r1: Point
    r2: Point


class Cuboid(BaseInstance):
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
    tags: List[Tags]
    instances: Optional[List[Union[Template, Cuboid, Point, PolyLine, Polygon, Bbox, Ellipse]]]

    @validator("instances", pre=True, each_item=True)
    def check_instances(cls, instance):
        # todo add type checking
        annotation_type = instance.get("type")
        result = validate_model(ANNOTATION_TYPES[annotation_type], instance)
        if result[2]:
            raise ValidationError(result[2].raw_errors, model=ANNOTATION_TYPES[annotation_type])
        return instance
