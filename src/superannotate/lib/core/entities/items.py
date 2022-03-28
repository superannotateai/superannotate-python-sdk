from typing import Optional

from lib.core.entities.base import BaseEntity
from lib.core.enums import SegmentationStatus
from pydantic import Extra
from pydantic import Field


class Entity(BaseEntity):
    class Config:
        extra = Extra.allow


class TmpImageEntity(Entity):
    prediction_status: Optional[SegmentationStatus] = Field(
        SegmentationStatus.NOT_STARTED
    )
    segmentation_status: Optional[SegmentationStatus] = Field(
        SegmentationStatus.NOT_STARTED
    )
    approval_status: bool = None

    class Config:
        extra = Extra.ignore


class VideoEntity(Entity):
    class Config:
        extra = Extra.ignore


class DocumentEntity(Entity):
    class Config:
        extra = Extra.ignore
