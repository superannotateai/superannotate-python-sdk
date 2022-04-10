from lib.core.entities.base import TimedBaseModel
from lib.core.enums import IntegrationTypeEnum
from pydantic import Extra
from pydantic import Field


class IntegrationEntity(TimedBaseModel):
    id: int = None
    user_id: str = None
    name: str
    type: IntegrationTypeEnum = Field(None, alias="source")
    root: str = Field(None, alias="bucket_name")

    class Config:
        extra = Extra.ignore
