from typing import Optional

from lib.core.entities.base import BaseItemEntity
from lib.core.enums import ApprovalStatus
from lib.core.enums import SegmentationStatus
from lib.core.pydantic_v1 import Extra
from lib.core.pydantic_v1 import Field


class ImageEntity(BaseItemEntity):
    prediction_status: Optional[SegmentationStatus] = Field(
        SegmentationStatus.NOT_STARTED
    )
    segmentation_status: Optional[SegmentationStatus] = Field(
        SegmentationStatus.NOT_STARTED
    )
    approval_status: Optional[ApprovalStatus] = Field(None)
    is_pinned: Optional[bool]
    meta: Optional[dict]

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
