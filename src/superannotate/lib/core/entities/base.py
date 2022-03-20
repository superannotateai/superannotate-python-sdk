from datetime import datetime

from pydantic import BaseModel
from pydantic import Field


class TimedBaseModel(BaseModel):
    created_at: datetime = Field(None, alias="createdAt")
    updated_at: datetime = Field(None, alias="updatedAt")
