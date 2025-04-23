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
from lib.core.pydantic_v1 import Extra
from lib.core.pydantic_v1 import Field
from lib.core.pydantic_v1 import parse_datetime
from lib.core.pydantic_v1 import StrictBool
from lib.core.pydantic_v1 import StrictFloat
from lib.core.pydantic_v1 import StrictInt
from lib.core.pydantic_v1 import StrictStr


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
    createdAt: Optional[StringDate] = None
    updatedAt: Optional[StringDate] = None


class AttachmentEntity(BaseModel):
    name: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    url: str
    integration: Optional[str] = None
    integration_id: Optional[int] = None

    class Config:
        extra = Extra.ignore

    def __hash__(self):
        return hash(self.name)


class StepEntity(BaseModel):
    id: Optional[int]
    project_id: Optional[int]
    class_id: Optional[int]
    className: Optional[str]
    step: Optional[int]
    tool: Optional[int]
    attribute: List = tuple()

    class Config:
        extra = Extra.ignore

    def __copy__(self):
        return StepEntity(step=self.step, tool=self.tool, attribute=self.attribute)


class SettingEntity(BaseModel):
    id: Optional[int]
    project_id: Optional[int]
    attribute: str
    value: Union[StrictStr, StrictInt, StrictFloat, StrictBool]  # todo set any

    class Config:
        extra = Extra.ignore

    def __copy__(self):
        return SettingEntity(attribute=self.attribute, value=self.value)


class ContributorEntity(BaseModel):
    first_name: Optional[str]
    last_name: Optional[str]
    user_id: str
    user_role: Union[int, str]

    class Config:
        extra = Extra.ignore


class WorkflowEntity(TimedBaseModel):
    id: Optional[int]
    name: Optional[str]
    type: Optional[str]
    description: Optional[str]
    raw_config: Optional[dict]

    def is_system(self):
        return self.type == "system"

    class Config:
        extra = Extra.ignore


class ProjectEntity(TimedBaseModel):
    id: Optional[int]
    team_id: Optional[int]
    name: str
    type: ProjectType
    description: Optional[str]
    instructions_link: Optional[str]
    creator_id: Optional[str]
    entropy_status: Optional[int]
    sharing_status: Optional[int]
    status: Optional[ProjectStatus]
    folder_id: Optional[int]
    workflow_id: Optional[int]
    workflow: Optional[WorkflowEntity]
    sync_status: Optional[int]
    upload_state: Optional[int]
    users: Optional[List[ContributorEntity]] = []
    unverified_users: Optional[List[Any]] = []
    contributors: List[ContributorEntity] = []
    settings: List[SettingEntity] = []
    classes: List[AnnotationClassEntity] = []
    item_count: Optional[int] = Field(None, alias="imageCount")
    completed_items_count: Optional[int] = Field(None, alias="completedImagesCount")
    root_folder_completed_items_count: Optional[int] = Field(
        None, alias="rootFolderCompletedImagesCount"
    )
    custom_fields: dict = {}

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
            workflow_id=self.workflow_id,
        )

    def __eq__(self, other):
        return self.id == other.id


class UserEntity(BaseModel):
    id: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[str]
    user_role: Optional[int]

    class Config:
        extra = Extra.ignore


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
    owner_id: Optional[str]
    scores: Optional[List[str]]

    class Config:
        extra = Extra.ignore


class CustomFieldEntity(BaseModel):
    ...

    class Config:
        extra = Extra.allow
