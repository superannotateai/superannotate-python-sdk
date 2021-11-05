from typing import List
from typing import Optional

from lib.core.entities.utils import Attribute
from lib.core.entities.utils import BaseInstance
from lib.core.entities.utils import MetadataBase
from lib.core.entities.utils import Tag
from pydantic import BaseModel
from pydantic import Field


class Metadata(MetadataBase):
    pass


class DocumentInstance(BaseInstance):
    start: int
    end: int
    attributes: Optional[List[Attribute]] = Field(list())


class DocumentAnnotation(BaseModel):
    metadata: Metadata
    instances: Optional[List[DocumentInstance]] = Field(list())
    tags: Optional[List[Tag]] = Field(list())
    # TODO check free_text: str = Field(alias="freeText")
