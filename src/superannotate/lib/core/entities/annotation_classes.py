from pydantic import BaseModel
from pydantic import StrictStr
from pydantic import StrictBool
from typing import List


class Attribute(BaseModel):
    name: StrictStr


class AttributeGroup(BaseModel):
    name: StrictStr
    is_multiselect: StrictBool
    attributes: List[Attribute]


class AnnotationClass(BaseModel):
    name : StrictStr
    color: StrictStr
    attribute_groups: List[AttributeGroup]
