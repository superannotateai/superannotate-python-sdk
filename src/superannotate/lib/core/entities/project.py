import datetime
import uuid
from typing import Any
from typing import List
from typing import Optional
from typing import Union

from lib.core.entities.base import BaseModel
from lib.core.entities.classes import AnnotationClassEntity
from lib.core.enums import BaseTitledEnum
from lib.core.enums import ProjectStatus
from lib.core.enums import ProjectType
from lib.core.enums import UserRole
from pydantic import Extra
from pydantic import Field
from pydantic import StrictBool
from pydantic import StrictFloat
from pydantic import StrictInt
from pydantic import StrictStr
from pydantic.datetime_parse import parse_datetime


class StringDate(datetime.datetime):
    @classmethod
    def __get_validators__(cls):
        yield parse_datetime
        yield cls.validate

    @classmethod
    def validate(cls, v: datetime):
        v = v.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        return v


class TimedBaseModel(BaseModel):
    createdAt: Optional[StringDate] = Field(
        None, alias="createdAt", description="Date of creation"
    )
    updatedAt: Optional[StringDate] = Field(
        None, alias="updatedAt", description="Update date"
    )


class AttachmentEntity(BaseModel):
    name: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    url: str

    class Config:
        extra = Extra.ignore

    def __hash__(self):
        return hash(self.name)


class WorkflowEntity(BaseModel):
    id: Optional[int]
    project_id: Optional[int]
    class_id: Optional[int]
    className: Optional[str]
    step: Optional[int]
    tool: Optional[int]
    attribute: List = (tuple(),)

    def __copy__(self):
        return WorkflowEntity(step=self.step, tool=self.tool, attribute=self.attribute)


class SettingEntity(BaseModel):
    id: Optional[int]
    project_id: Optional[int]
    attribute: str
    value: Union[StrictStr, StrictInt, StrictFloat, StrictBool]

    class Config:
        extra = Extra.ignore

    def __copy__(self):
        return SettingEntity(attribute=self.attribute, value=self.value)


class ContributorEntity(BaseModel):
    first_name: Optional[str]
    last_name: Optional[str]
    user_id: str
    user_role: UserRole

    class Config:
        extra = Extra.ignore


class ProjectEntity(TimedBaseModel):
    id: Optional[int]
    team_id: Optional[int]
    name: Optional[str]
    type: Optional[ProjectType]
    description: Optional[str]
    instructions_link: Optional[str]
    creator_id: Optional[str]
    entropy_status: Optional[int]
    sharing_status: Optional[int]
    status: Optional[ProjectStatus]
    folder_id: Optional[int]
    sync_status: Optional[int]
    upload_state: Optional[int]
    users: Optional[List[ContributorEntity]] = []
    unverified_users: Optional[List[Any]] = []
    contributors: List[ContributorEntity] = []
    settings: List[SettingEntity] = []
    classes: List[AnnotationClassEntity] = []
    workflows: Optional[List[WorkflowEntity]] = []
    item_count: Optional[int] = Field(None, alias="imageCount")
    completed_items_count: Optional[int] = Field(None, alias="completedImagesCount")
    root_folder_completed_items_count: Optional[int] = Field(
        None, alias="rootFolderCompletedImagesCount"
    )

    class Config:
        extra = Extra.ignore
        use_enum_names = True
        json_encoders = {
            BaseTitledEnum: lambda v: v.value,
            datetime.date: lambda v: v.isoformat(),
            datetime.datetime: lambda v: v.isoformat(),
        }

    def __copy__(self):
        return ProjectEntity(
            team_id=self.team_id,
            name=self.name,
            type=self.type,
            description=f"Copy of {self.name}.",
            instructions_link=self.instructions_link,
            status=self.status,
            folder_id=self.folder_id,
            users=self.users,
            settings=[s.__copy__() for s in self.settings],
            upload_state=self.upload_state,
        )


class MLModelEntity(TimedBaseModel):
    id: Optional[int]
    team_id: Optional[int]
    name: Optional[str]
    path: Optional[str]
    config_path: Optional[str]
    model_type: Optional[int]
    description: Optional[str]
    output_path: Optional[str]
    task: Optional[str]
    base_model_id: Optional[int]
    image_count: Optional[int]
    training_status: Optional[int]
    test_folder_ids: Optional[List[int]]
    train_folder_ids: Optional[List[int]]
    is_trainable: Optional[bool]
    is_global: Optional[bool]
    hyper_parameters: Optional[dict]

    class Config:
        extra = Extra.ignore


class UserEntity(BaseModel):
    id: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[str]
    picture: Optional[str]
    user_role: Optional[int]


class TeamEntity(BaseModel):
    id: Optional[int]
    name: Optional[str]
    description: Optional[str]
    type: Optional[str]
    user_role: Optional[str]
    is_default: Optional[bool]
    users: Optional[List[UserEntity]]
    pending_invitations: Optional[List[Any]]
    creator_id: Optional[str]
