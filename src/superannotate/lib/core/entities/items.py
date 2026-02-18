from typing import List
from typing import Optional

from pydantic import ConfigDict
from pydantic import Field

from lib.core.entities.base import BaseItemEntity
from lib.core.entities.project import TimedBaseModel
from lib.core.enums import ApprovalStatus
from lib.core.enums import ProjectType


class ImageEntity(BaseItemEntity):
    model_config = ConfigDict(extra="ignore")

    approval_status: Optional[ApprovalStatus] = Field(default=None)
    is_pinned: Optional[bool] = None
    meta: Optional[dict] = None


class CategoryEntity(TimedBaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: int
    value: str = Field(default=None, alias="name")


class ProjectCategoryEntity(TimedBaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    name: str
    project_id: int


class MultiModalItemCategoryEntity(TimedBaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: int = Field(default=None, alias="category_id")
    value: str = Field(default=None, alias="category_name")


class MultiModalItemEntity(BaseItemEntity):
    model_config = ConfigDict(extra="ignore")

    categories: Optional[List[MultiModalItemCategoryEntity]] = None


class VideoEntity(BaseItemEntity):
    model_config = ConfigDict(extra="ignore")

    approval_status: Optional[ApprovalStatus] = Field(default=None)


class DocumentEntity(BaseItemEntity):
    model_config = ConfigDict(extra="ignore")

    approval_status: Optional[ApprovalStatus] = Field(default=None)


class TiledEntity(BaseItemEntity):
    model_config = ConfigDict(extra="ignore")


class ClassificationEntity(BaseItemEntity):
    model_config = ConfigDict(extra="ignore")


class PointCloudEntity(BaseItemEntity):
    model_config = ConfigDict(extra="ignore")


PROJECT_ITEM_ENTITY_MAP = {
    ProjectType.VECTOR: ImageEntity,
    ProjectType.PIXEL: ImageEntity,
    ProjectType.TILED: ImageEntity,
    ProjectType.VIDEO: VideoEntity,
    ProjectType.DOCUMENT: DocumentEntity,
    ProjectType.MULTIMODAL: MultiModalItemEntity,
}
