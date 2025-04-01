from typing import List
from typing import Optional

from lib.core.entities.base import BaseItemEntity
from lib.core.entities.project import TimedBaseModel
from lib.core.enums import ApprovalStatus
from lib.core.enums import ProjectType
from lib.core.pydantic_v1 import Extra
from lib.core.pydantic_v1 import Field


class ImageEntity(BaseItemEntity):
    approval_status: Optional[ApprovalStatus] = Field(None)
    is_pinned: Optional[bool]
    meta: Optional[dict]

    class Config:
        extra = Extra.ignore


class CategoryEntity(TimedBaseModel):
    id: int
    value: str = Field(None, alias="name")

    class Config:
        extra = Extra.ignore


class MultiModalItemCategoryEntity(TimedBaseModel):
    id: int = Field(None, alias="category_id")
    value: str = Field(None, alias="category_name")

    class Config:
        extra = Extra.ignore


class MultiModalItemEntity(BaseItemEntity):
    categories: Optional[List[MultiModalItemCategoryEntity]]

    class Config:
        extra = Extra.ignore


class VideoEntity(BaseItemEntity):
    approval_status: Optional[ApprovalStatus] = Field(None)

    class Config:
        extra = Extra.ignore


class DocumentEntity(BaseItemEntity):
    approval_status: Optional[ApprovalStatus] = Field(None)

    class Config:
        extra = Extra.ignore


class TiledEntity(BaseItemEntity):
    class Config:
        extra = Extra.ignore


class ClassificationEntity(BaseItemEntity):
    class Config:
        extra = Extra.ignore


class PointCloudEntity(BaseItemEntity):
    class Config:
        extra = Extra.ignore


PROJECT_ITEM_ENTITY_MAP = {
    ProjectType.VECTOR: ImageEntity,
    ProjectType.PIXEL: ImageEntity,
    ProjectType.TILED: ImageEntity,
    ProjectType.VIDEO: VideoEntity,
    ProjectType.DOCUMENT: DocumentEntity,
    ProjectType.MULTIMODAL: MultiModalItemEntity,
}
