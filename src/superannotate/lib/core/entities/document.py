from typing import List
from typing import Optional

from lib.core.entities.utils import MetadataBase
from lib.core.entities.utils import BaseInstance
from lib.core.entities.utils import Attribute
from lib.core.entities.utils import Tag

from pydantic import BaseModel
from pydantic import Field


class DocumentInstance(BaseInstance):
    start: int
    end: int
    attributes: List[Attribute]


class DocumentAnnotation(BaseModel):
    metadata: MetadataBase
    instances: List[DocumentInstance]
    tags: Optional[List[Tag]]
    free_text: str = Field(alias="freeText")



