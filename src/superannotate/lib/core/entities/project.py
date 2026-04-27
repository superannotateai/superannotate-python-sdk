from __future__ import annotations

import uuid
from typing import Any

from lib.core.entities.base import TimedBaseModel
from lib.core.entities.classes import AnnotationClassEntity
from lib.core.entities.work_managament import WMProjectUserEntity
from lib.core.enums import ProjectStatus
from lib.core.enums import ProjectType
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import StrictBool
from pydantic import StrictFloat
from pydantic import StrictInt
from pydantic import StrictStr


class AttachmentEntity(BaseModel):
    name: str | None = Field(default_factory=lambda: str(uuid.uuid4()))
    url: str
    integration: str | None = None
    integration_id: int | None = None
    model_config = ConfigDict(extra="ignore")

    def __hash__(self):
        return hash(self.name)


class StepEntity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int | None = None
    project_id: int | None = None
    class_id: int | None = None
    className: str | None = None
    step: int | None = None
    tool: int | None = None
    attribute: list = Field(default_factory=list)

    def __copy__(self):
        return StepEntity(step=self.step, tool=self.tool, attribute=self.attribute)


class SettingEntity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int | None = None
    project_id: int | None = None
    attribute: str
    value: StrictStr | StrictInt | StrictFloat | StrictBool | None = None

    def __copy__(self):
        return SettingEntity(attribute=self.attribute, value=self.value)


class WorkflowEntity(TimedBaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int | None = None
    name: str | None = None
    type: str | None = None
    description: str | None = None

    def is_system(self):
        return self.type == "system"


class ProjectEntity(TimedBaseModel):
    model_config = ConfigDict(extra="ignore", use_enum_values=False)

    id: int | None = None
    team_id: int | None = None
    name: str
    type: ProjectType
    description: str | None = None
    instructions_link: str | None = None
    creator_id: str | None = None
    entropy_status: int | None = None
    sharing_status: int | None = None
    status: ProjectStatus | None = None
    folder_id: int | None = None
    workflow_id: int | None = None
    workflow: WorkflowEntity | None = None
    sync_status: int | None = None
    upload_state: int | None = None
    contributors: list[WMProjectUserEntity] = Field(default_factory=list)
    settings: list[SettingEntity] = Field(default_factory=list)
    classes: list[AnnotationClassEntity] = Field(default_factory=list)
    item_count: int | None = Field(None, alias="imageCount")
    completed_items_count: int | None = Field(None, alias="completedImagesCount")
    root_folder_completed_items_count: int | None = Field(
        None, alias="rootFolderCompletedImagesCount"
    )
    custom_fields: dict = Field(default_factory=dict)

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

    id: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    user_role: int | None = None


class TeamEntity(BaseModel):
    model_config = ConfigDict(extra="ignore", coerce_numbers_to_str=True)

    id: int | None = None
    name: str | None = None
    description: str | None = None
    type: str | None = None
    user_role: int | None = None
    is_default: bool | None = None
    users: list[UserEntity] | None = None
    pending_invitations: list[Any] | None = None
    creator_id: str | None = None
    owner_id: str | None = None
    scores: list[str] | None = None


class CustomFieldEntity(BaseModel):
    model_config = ConfigDict(extra="allow")
