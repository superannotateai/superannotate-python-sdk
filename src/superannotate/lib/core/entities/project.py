import datetime
import uuid
from typing import Annotated
from typing import Any
from typing import List
from typing import Optional
from typing import Union

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import StrictBool
from pydantic import StrictFloat
from pydantic import StrictInt
from pydantic import StrictStr
from pydantic.functional_validators import BeforeValidator

from lib.core.entities.classes import AnnotationClassEntity
from lib.core.entities.work_managament import WMProjectUserEntity
from lib.core.enums import BaseTitledEnum
from lib.core.enums import ProjectStatus
from lib.core.enums import ProjectType


def _parse_string_date_project(v: Any) -> Optional[str]:
    """Parse datetime to string format for project."""
    if v is None:
        return None
    if isinstance(v, str):
        return v
    if isinstance(v, datetime.datetime):
        return v.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    try:
        from dateutil.parser import parse

        dt = parse(str(v))
        return dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    except Exception:
        return str(v)


StringDate = Annotated[Optional[str], BeforeValidator(_parse_string_date_project)]


class TimedBaseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    createdAt: StringDate = None
    updatedAt: StringDate = None


class AttachmentEntity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    url: str
    integration: Optional[str] = None
    integration_id: Optional[int] = None

    def __hash__(self):
        return hash(self.name)


class StepEntity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Optional[int] = None
    project_id: Optional[int] = None
    class_id: Optional[int] = None
    className: Optional[str] = None
    step: Optional[int] = None
    tool: Optional[int] = None
    attribute: List = Field(default_factory=list)

    def __copy__(self):
        return StepEntity(step=self.step, tool=self.tool, attribute=self.attribute)


class SettingEntity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Optional[int] = None
    project_id: Optional[int] = None
    attribute: str
    value: Union[StrictStr, StrictInt, StrictFloat, StrictBool]  # todo set any

    def __copy__(self):
        return SettingEntity(attribute=self.attribute, value=self.value)


class WorkflowEntity(TimedBaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Optional[int] = None
    name: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    raw_config: Optional[dict] = None

    def is_system(self):
        return self.type == "system"


class ProjectEntity(TimedBaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: Optional[int] = None
    team_id: Optional[int] = None
    name: str
    type: ProjectType
    description: Optional[str] = None
    instructions_link: Optional[str] = None
    creator_id: Optional[str] = None
    entropy_status: Optional[int] = None
    sharing_status: Optional[int] = None
    status: Optional[ProjectStatus] = None
    folder_id: Optional[int] = None
    workflow_id: Optional[int] = None
    workflow: Optional[WorkflowEntity] = None
    sync_status: Optional[int] = None
    upload_state: Optional[int] = None
    contributors: List[WMProjectUserEntity] = []
    settings: List[SettingEntity] = []
    classes: List[AnnotationClassEntity] = []
    item_count: Optional[int] = Field(default=None, alias="imageCount")
    completed_items_count: Optional[int] = Field(
        default=None, alias="completedImagesCount"
    )
    root_folder_completed_items_count: Optional[int] = Field(
        default=None, alias="rootFolderCompletedImagesCount"
    )
    custom_fields: dict = {}

    def __copy__(self):
        return ProjectEntity(
            team_id=self.team_id,
            name=self.name,
            type=self.type,
            description=f"Copy of {self.name}.",
            instructions_link=self.instructions_link,
            status=self.status,
            folder_id=self.folder_id,
            contributors=self.contributors,
            settings=[s.__copy__() for s in self.settings],
            upload_state=self.upload_state,
            workflow_id=self.workflow_id,
        )

    def __eq__(self, other):
        return self.id == other.id


class UserEntity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    user_role: Optional[int] = None


class TeamEntity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    is_default: Optional[bool] = None
    users: Optional[List[UserEntity]] = None
    pending_invitations: Optional[List[Any]] = None
    creator_id: Optional[str] = None
    owner_id: Optional[str] = None
    scores: Optional[List[str]] = None


class CustomFieldEntity(BaseModel):
    model_config = ConfigDict(extra="allow")
