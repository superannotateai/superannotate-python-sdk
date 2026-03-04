from typing import List
from typing import Optional

from lib.core.entities.base import BaseItemEntity
from lib.core.entities.project import TimedBaseModel
from lib.core.enums import ApprovalStatus
from lib.core.enums import ProjectType
from pydantic import ConfigDict
from pydantic import Field


class ImageEntity(BaseItemEntity):
    approval_status: Optional[ApprovalStatus] = Field(None)
    is_pinned: Optional[bool] = Field(None)
    meta: Optional[dict] = Field(None)
    model_config = ConfigDict(extra="ignore")


class CategoryEntity(TimedBaseModel):
    id: int
    value: str = Field(None, alias="name")
    model_config = ConfigDict(extra="ignore")


class ProjectCategoryEntity(TimedBaseModel):
    id: int
    name: str
    project_id: int
    model_config = ConfigDict(extra="ignore")


class MultiModalItemCategoryEntity(TimedBaseModel):
    id: int = Field(None, alias="category_id")
    value: str = Field(None, alias="category_name")
    model_config = ConfigDict(extra="ignore")


class MultiModalItemEntity(BaseItemEntity):
    categories: Optional[List[MultiModalItemCategoryEntity]] = None
    model_config = ConfigDict(extra="ignore")


class VideoEntity(BaseItemEntity):
    approval_status: Optional[ApprovalStatus] = Field(None)
    model_config = ConfigDict(extra="ignore")


class DocumentEntity(BaseItemEntity):
    approval_status: Optional[ApprovalStatus] = Field(None)
    model_config = ConfigDict(extra="ignore")


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
