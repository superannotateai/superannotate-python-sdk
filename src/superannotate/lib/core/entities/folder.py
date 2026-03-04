from typing import List
from typing import Optional

from lib.core.entities.base import TimedBaseModel
from lib.core.enums import FolderStatus
from lib.core.enums import WMUserStateEnum
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator


class FolderUserEntity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email: Optional[str] = None
    id: Optional[int] = None
    role: Optional[int] = None
    state: Optional[WMUserStateEnum] = None


class FolderEntity(TimedBaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Optional[int] = None
    name: Optional[str] = None
    status: Optional[FolderStatus] = None
    project_id: Optional[int] = None
    team_id: Optional[int] = None
    is_root: Optional[bool] = False
    contributors: Optional[List[FolderUserEntity]] = Field(
        default_factory=list, alias="folderUsers"
    )
    completedCount: Optional[int] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_folder_users(cls, values: dict) -> dict:
        if not isinstance(values, dict):
            return values
        folder_users = values.get("folderUsers")
        if not folder_users:
            return values

        normalized: List[dict] = []
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
