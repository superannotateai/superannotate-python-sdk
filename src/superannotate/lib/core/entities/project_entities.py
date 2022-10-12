from abc import ABC
from abc import abstractmethod
from typing import Any


class BaseEntity(ABC):
    def __init__(self, uuid: Any = None):
        self._uuid = uuid

    @property
    def id(self):
        return self._uuid

    @property
    def uuid(self):
        return self._uuid

    @uuid.setter
    def uuid(self, value: Any):
        self._uuid = value

    @abstractmethod
    def to_dict(self):
        raise NotImplementedError


class ConfigEntity(BaseEntity):
    def __init__(self, uuid: str, value: str):
        super().__init__(uuid)
        self._value = value

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value

    def to_dict(self):
        return {"key": self.uuid, "value": self.value}


class ImageInfoEntity(BaseEntity):
    def __init__(
        self,
        uuid=None,
        width: float = None,
        height: float = None,
    ):
        super().__init__(uuid),
        self.width = width
        self.height = height

    def to_dict(self):
        return {
            "width": self.width,
            "height": self.height,
        }


# class ImageEntity(BaseEntity):
#     def __init__(
#         self,
#         uuid: int = None,
#         name: str = None,
#         path: str = None,
#         project_id: int = None,
#         team_id: int = None,
#         annotation_status_code: int = None,
#         folder_id: int = None,
#         annotator_id: int = None,
#         annotator_name: str = None,
#         qa_id: str = None,
#         qa_name: str = None,
#         entropy_value: int = None,
#         approval_status: bool = None,
#         is_pinned: bool = None,
#         segmentation_status: int = SegmentationStatus.NOT_STARTED.value,
#         prediction_status: int = SegmentationStatus.NOT_STARTED.value,
#         meta: ImageInfoEntity = ImageInfoEntity(),
#         created_at: str = None,
#         updated_at: str = None,
#         **_,
#     ):
#         super().__init__(uuid)
#         self.team_id = team_id
#         self.name = name
#         self.path = path
#         self.project_id = project_id
#         self.project_id = project_id
#         self.annotation_status_code = annotation_status_code
#         self.folder_id = folder_id
#         self.qa_id = qa_id
#         self.qa_name = qa_name
#         self.entropy_value = entropy_value
#         self.annotator_id = annotator_id
#         self.approval_status = approval_status
#         self.annotator_name = annotator_name
#         self.is_pinned = is_pinned
#         self.segmentation_status = segmentation_status
#         self.prediction_status = prediction_status
#         self.meta = meta
#         self.created_at = created_at
#         self.updated_at = updated_at
#
#     @staticmethod
#     def from_dict(**kwargs):
#         if "id" in kwargs:
#             kwargs["uuid"] = kwargs["id"]
#             del kwargs["id"]
#         if "annotation_status" in kwargs:
#             kwargs["annotation_status_code"] = kwargs["annotation_status"]
#             del kwargs["annotation_status"]
#         if "createdAt" in kwargs:
#             kwargs["created_at"] = kwargs["createdAt"]
#             del kwargs["createdAt"]
#         if "updatedAt" in kwargs:
#             kwargs["updated_at"] = kwargs["updatedAt"]
#             del kwargs["updatedAt"]
#         return ImageEntity(**kwargs)
#
#     def to_dict(self):
#         data = {
#             "id": self.uuid,
#             "team_id": self.team_id,
#             "project_id": self.project_id,
#             "folder_id": self.folder_id,
#             "name": self.name,
#             "path": self.path,
#             "annotation_status": self.annotation_status_code,
#             "prediction_status": self.prediction_status,
#             "segmentation_status": self.segmentation_status,
#             "approval_status": self.approval_status,
#             "is_pinned": self.is_pinned,
#             "annotator_id": self.annotator_id,
#             "annotator_name": self.annotator_name,
#             "qa_id": self.qa_id,
#             "qa_name": self.qa_name,
#             "entropy_value": self.entropy_value,
#             "createdAt": self.created_at,
#             "updatedAt": self.updated_at,
#             "meta": self.meta.to_dict(),
#         }
#         return {k: v for k, v in data.items() if v is not None}


class S3FileEntity(BaseEntity):
    def __init__(self, uuid, data, metadata: dict = None):
        super().__init__(uuid)
        self.data = data
        self.metadata = metadata

    def to_dict(self):
        return {"uuid": self.uuid, "bytes": self.data, "metadata": self.metadata}
