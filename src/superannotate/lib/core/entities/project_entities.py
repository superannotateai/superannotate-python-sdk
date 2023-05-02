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


class S3FileEntity(BaseEntity):
    def __init__(self, uuid, data, metadata: dict = None):
        super().__init__(uuid)
        self.data = data
        self.metadata = metadata

    def to_dict(self):
        return {"uuid": self.uuid, "bytes": self.data, "metadata": self.metadata}
