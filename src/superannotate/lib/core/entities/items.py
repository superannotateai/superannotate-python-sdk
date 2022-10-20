from typing import Optional

from lib.core.entities.base import BaseItemEntity
from lib.core.enums import ApprovalStatus
from lib.core.enums import SegmentationStatus
from pydantic import Extra
from pydantic import Field


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
    class Config:
        extra = Extra.ignore
