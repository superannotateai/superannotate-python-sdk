from pydantic import Field
from lib.core.entities.base import TimedBaseModel


class IntegrationEntity(TimedBaseModel):
    id: int = None
    user_id: str = None
    name: str
    type: str = "aws"
    root: str = Field(None, alias="bucket_name")
    source: int = None

    class Config:
        arbitrary_types_allowed = True
