from enum import Enum
from typing import List
from typing import Optional

from lib.core.entities.base import BaseModel
from lib.core.entities.base import TimedBaseModel
from lib.core.enums import FolderStatus
from lib.core.enums import WMUserStateEnum
from lib.core.pydantic_v1 import Extra
from lib.core.pydantic_v1 import Field
from lib.core.pydantic_v1 import root_validator


class FolderUserEntity(BaseModel):
    email: Optional[str] = None
    id: Optional[int] = None
    role: Optional[int] = None
    state: Optional[WMUserStateEnum] = None

    class Config:
        use_enum_names = True
        allow_population_by_field_name = True
        extra = Extra.ignore
        json_encoders = {Enum: lambda v: v.value}


class FolderEntity(TimedBaseModel):
    id: Optional[int]
    name: Optional[str]
    status: Optional[FolderStatus]
    project_id: Optional[int]
    team_id: Optional[int]
    is_root: Optional[bool] = False
    contributors: Optional[List[FolderUserEntity]] = Field(
        default_factory=list, alias="folderUsers"
    )

    completedCount: Optional[int]

    @root_validator(pre=True)
    def normalize_folder_users(cls, values: dict) -> dict:
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

    class Config:
        extra = Extra.ignore
        allow_population_by_field_name = True
