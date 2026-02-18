from pydantic import ConfigDict
from pydantic import Field

from lib.core.entities.base import TimedBaseModel
from lib.core.enums import IntegrationTypeEnum


class IntegrationEntity(TimedBaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: int = None
    creator_id: str = None
    name: str
    type: IntegrationTypeEnum = Field(default=None, alias="source")
    root: str = Field(default=None, alias="bucket_name")
