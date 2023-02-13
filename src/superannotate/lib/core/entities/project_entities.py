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


class S3FileEntity(BaseEntity):
    def __init__(self, uuid, data, metadata: dict = None):
        super().__init__(uuid)
        self.data = data
        self.metadata = metadata

    def to_dict(self):
        return {"uuid": self.uuid, "bytes": self.data, "metadata": self.metadata}
