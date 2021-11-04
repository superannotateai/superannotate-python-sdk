from typing import List
from typing import Optional

from utils import MetadataBase
from utils import BaseInstance
from utils import Attribute
from utils import Tag

from pydantic import BaseModel


class Metadata(MetadataBase):
    pass


class DocumentInstance(BaseInstance):
    start: int
    end: int
    attributes: List[Attribute]


class DocumentAnnotation(BaseModel):
    metadata: Metadata
    instances: List[DocumentInstance]
    tags: Optional[List[Tag]]
    # TODO check free_text: str = Field(alias="freeText")



