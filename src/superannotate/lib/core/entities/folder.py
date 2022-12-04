from typing import List
from typing import Optional

from lib.core.entities.base import TimedBaseModel
from lib.core.enums import FolderStatus
from pydantic import Extra


class FolderEntity(TimedBaseModel):
    id: Optional[int]
    name: Optional[str]
    status: Optional[FolderStatus]
    project_id: Optional[int]
    parent_id: Optional[int]
    team_id: Optional[int]
    is_root: Optional[bool] = (False,)
    folder_users: Optional[List[dict]]
    completedCount: Optional[int]

    class Config:
        extra = Extra.allow
