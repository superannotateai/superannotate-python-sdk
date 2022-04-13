import uuid
from datetime import datetime
from typing import Optional
from typing import List
from typing import Any
from typing import Union

from lib.core.enums import AnnotationStatus
from pydantic import BaseModel
from pydantic import Extra
from pydantic import Field
from pydantic import StrictFloat
from pydantic import StrictInt
from pydantic import StrictStr


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


class AttachmentEntity(BaseModel):
    name: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    url: str

    class Config:
        extra = Extra.ignore


class SettingEntity(BaseModel):
    id: Optional[int]
    project_id: Optional[int]
    attribute: str
    value: Union[StrictStr, StrictInt, StrictFloat]

    class Config:
        extra = Extra.ignore

    def __copy__(self):
        return SettingEntity(attribute=self.attribute, value=self.value)


class ProjectEntity(TimedBaseModel):
    id: Optional[int]
    team_id: Optional[int]
    name: Optional[str]
    type: Optional[int]
    description: Optional[str]
    instructions_link: Optional[str]
    creator_id: Optional[str]
    entropy_status: Optional[int]
    sharing_status: Optional[int]
    status: Optional[int]
    folder_id: Optional[int]
    sync_status: Optional[int]
    upload_state: Optional[int]
    users: Optional[List[Any]] = []
    unverified_users: Optional[List[Any]] = []
    contributors: Optional[List[Any]] = []
    settings: Optional[List[SettingEntity]] = []
    classes: Optional[List[Any]] = []
    workflows: Optional[List[Any]] = []
    completed_images_count: Optional[int] = Field(None, alias="completedImagesCount")
    root_folder_completed_images_count: Optional[int] = Field(None, alias="rootFolderCompletedImagesCount")

    class Config:
        extra = Extra.ignore

    def __copy__(self):
        return ProjectEntity(
            team_id=self.team_id,
            name=self.name,
            type=self.type,
            description=self.description,
            instructions_link=self.instructions_link
            if self.description
            else f"Copy of {self.name}.",
            status=self.status,
            folder_id=self.folder_id,
            users=self.users,
            upload_state=self.upload_state,
        )
