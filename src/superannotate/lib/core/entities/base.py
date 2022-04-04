from datetime import datetime
from typing import Optional

from lib.core.enums import AnnotationStatus
from pydantic import BaseModel
from pydantic import Extra
from pydantic import Field


class TimedBaseModel(BaseModel):
    createdAt: datetime = Field(None, alias="createdAt")
    updatedAt: datetime = Field(None, alias="updatedAt")


class BaseEntity(TimedBaseModel):
    name: str
    path: Optional[str] = Field(None, description="Item’s path in SuperAnnotate project")
    url: Optional[str] = Field(description="Publicly available HTTP address")
    annotator_email: Optional[str] = Field(description="Annotator email")
    qa_email: Optional[str] = Field(description="QA email")
    annotation_status: AnnotationStatus = Field(description="Item annotation status")
    entropy_value: Optional[float] = Field(description="Priority score of given item")
    createdAt: str = Field(description="Date of creation")
    updatedAt: str = Field(description="Update date")

    class Config:
        extra = Extra.allow
