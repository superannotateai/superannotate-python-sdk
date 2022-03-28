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
    id: int
    name: str
    path: Optional[str] = Field(
        None, description="Item’s path in SuperAnnotate project"
    )
    url: Optional[str] = Field(None, description="Publicly available HTTP address")
    annotation_status: AnnotationStatus = Field(description="Item annotation status")
    annotator_name: Optional[str] = Field(description="Annotator email")
    qa_name: Optional[str] = Field(description="QA email")
    entropy_value: Optional[str] = Field(description="Priority score of given item")
    createdAt: str = Field(description="Date of creation")
    updatedAt: str = Field(description="Update date")

    class Config:
        extra = Extra.allow

    def add_path(self, project_name: str, folder_name: str):
        path = f"{project_name}{f'/{folder_name}' if folder_name != 'root' else ''}/{self.name}"
        self.path = path
        return self
