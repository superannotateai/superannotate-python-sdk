from typing import List
from typing import Optional

from pydantic import BaseModel


class DocumentAnnotation(BaseModel):
    instances: list
    tags: Optional[List[str]]
