from lib.core.entities.base import TimedBaseModel
from lib.core.enums import IntegrationTypeEnum
from pydantic import ConfigDict
from pydantic import Field


class IntegrationEntity(TimedBaseModel):
    id: int = None
    creator_id: str | None = None
    name: str
    type: IntegrationTypeEnum = Field(None, alias="source")
    root: str = Field(None, alias="bucket_name")
    model_config = ConfigDict(extra="ignore")
