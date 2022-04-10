from typing import Optional

from lib.core.entities.base import BaseEntity
from lib.core.enums import SegmentationStatus
from pydantic import Extra
from pydantic import Field


class Entity(BaseEntity):

    class Config:
        extra = Extra.allow

    def add_path(self, project_name: str, folder_name: str):
        self.path = f"{project_name}{f'/{folder_name}' if folder_name != 'root' else ''}/{self.name}"
        return self

    @staticmethod
    def map_fields(entity: dict) -> dict:
        entity["url"] = entity.get("path")
        entity["path"] = None
        entity["annotator_email"] = entity.get("annotator_id")
        entity["qa_email"] = entity.get("qa_id")
        return entity


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
