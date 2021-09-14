from functools import wraps
from typing import List
from typing import Optional
from typing import Union

from lib.core.enums import AnnotationStatus
from pydantic import BaseModel
from pydantic import constr
from pydantic import StrictStr
from pydantic import validate_arguments as pydantic_validate_arguments
from pydantic import ValidationError


NotEmptyStr = constr(strict=True, min_length=1)


class Status(StrictStr):
    @classmethod
    def validate(cls, value: Union[str]) -> Union[str]:
        if cls.curtail_length and len(value) > cls.curtail_length:
            value = value[: cls.curtail_length]
        if value.lower() not in AnnotationStatus.values():
            raise TypeError(f"Available statuses is {', '.join(AnnotationStatus)}. ")
        return value


class AnnotationType(StrictStr):
    VALID_TYPES = ["bbox", "polygon", "point"]

    @classmethod
    def validate(cls, value: Union[str]) -> Union[str]:
        if value.lower() not in cls.VALID_TYPES:
            raise TypeError(
                f"Available annotation_types are {', '.join(cls.VALID_TYPES)}. "
            )
        return value


class Attribute(BaseModel):
    id: int
    group_id: int
    name: NotEmptyStr


class AttributeGroup(BaseModel):
    name: StrictStr
    is_multiselect: Optional[bool]
    attributes: List[Attribute]


class ClassesJson(BaseModel):
    name: StrictStr
    color: StrictStr
    attribute_groups: List[AttributeGroup]


class Metadata(BaseModel):
    width: int
    height: int


class BaseInstance(BaseModel):
    metadata: Metadata
    type: NotEmptyStr
    classId: int
    groupId: int
    attributes: List[Attribute]


class Point(BaseInstance):
    x: float
    y: float


class PolyLine(BaseInstance):
    points: List[float]


class Polygon(BaseInstance):
    points: List[float]


class BboxPoints(BaseModel):
    x1: float
    x2: float
    y1: float
    y2: float


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
    connections: List[TemplateConnection]
    templateId: int


class CuboidPoint(BaseModel):
    f1: Point
    f2: Point
    r1: Point
    r2: Point


class Cuboid(BaseInstance):
    points: List[CuboidPoint]


class VectorAnnotation(BaseModel):
    metadata: Metadata
    instances: Optional[List[Union[Template, Cuboid, Point, PolyLine, Polygon, Bbox, Ellipse]]]

def validate_arguments(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return pydantic_validate_arguments(func)(*args, **kwargs)
        except ValidationError as e:
            raise e

    return wrapped
