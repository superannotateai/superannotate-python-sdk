from __future__ import annotations

from lib.core.entities.base import TimedBaseModel
from lib.core.enums import FolderStatus
from lib.core.enums import WMUserStateEnum
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator


class FolderUserEntity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email: str | None = None
    id: int | None = None
    role: int | None = None
    state: WMUserStateEnum | None = None


class FolderEntity(TimedBaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int | None = None
    name: str | None = None
    status: FolderStatus | None = None
    project_id: int | None = None
    team_id: int | None = None
    is_root: bool | None = False
    contributors: list[FolderUserEntity] | None = Field(
        default_factory=list, alias="folderUsers"
    )
    completedCount: int | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_folder_users(cls, values: dict) -> dict:
        if not isinstance(values, dict):
            return values
        folder_users = values.get("folderUsers")
        if not folder_users:
            return values

        normalized: list[dict] = []
        for fu in folder_users:
            pu = fu.get("projectUser") or {}

            normalized.append(
                {
                    "email": pu.get("email"),
                    "id": pu.get("id"),
                    "role": pu.get("role"),
                    "state": pu.get("state"),
                }
            )

        values["folderUsers"] = normalized
        return values
