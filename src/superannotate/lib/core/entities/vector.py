from typing import List
from typing import Optional
from typing import Union

from lib.core.entities.utils import BaseModel
from lib.core.entities.utils import BaseVectorInstance
from lib.core.entities.utils import BboxPoints
from lib.core.entities.utils import Comment
from lib.core.entities.utils import INVALID_DICT_MESSAGE
from lib.core.entities.utils import Metadata
from lib.core.entities.utils import NotEmptyStr
from lib.core.entities.utils import Tag
from lib.core.entities.utils import VectorAnnotationTypeEnum
from pydantic import conlist
from pydantic import Field
from pydantic import StrictInt
from pydantic import ValidationError
from pydantic.error_wrappers import ErrorWrapper


class AxisPoint(BaseModel):
    x: float
    y: float


class Point(BaseVectorInstance, AxisPoint):
    pass


class PolyLine(BaseVectorInstance):
    points: conlist(float, min_items=2)


class Polygon(BaseVectorInstance):
    points: conlist(float, min_items=3)


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
    id: StrictInt
    x: float
    y: float


class TemplateConnection(BaseModel):
    id: StrictInt
    from_connection: StrictInt = Field(alias="from")
    to_connection: StrictInt = Field(alias="to")


class Template(BaseVectorInstance):
    points: conlist(TemplatePoint, min_items=1)
    connections: List[TemplateConnection]
    template_id: Optional[StrictInt] = Field(None, alias="templateId")
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
            try:
                instance_type = values["type"]
            except KeyError:
                raise ValidationError(
                    [ErrorWrapper(ValueError("field required"), "type")], cls
                )
            return ANNOTATION_TYPES[instance_type](**values)
        except KeyError:
            raise ValidationError(
                [
                    ErrorWrapper(
                        ValueError(
                            f"invalid type, valid types are {', '.join(ANNOTATION_TYPES.keys())}"
                        ),
                        "type",
                    )
                ],
                cls,
            )
        except TypeError as e:
            raise TypeError(INVALID_DICT_MESSAGE) from e


class VectorAnnotation(BaseModel):
    metadata: Metadata
    comments: Optional[List[Comment]] = Field(list())
    tags: Optional[List[Tag]] = Field(list())
    instances: Optional[List[AnnotationInstance]] = Field(list())
