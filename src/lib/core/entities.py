from abc import ABC
from abc import abstractmethod
from typing import Any


class BaseEntity(ABC):
    def __init__(self, uuid: Any = None):
        self._uuid = uuid

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


class ProjectEntity(BaseEntity):
    def __init__(
        self,
        uuid: int = None,
        team_id: int = None,
        name: str = None,
        project_type: int = None,
        description: str = None,
        status: int = None,
        folder_id: int = None,
    ):
        super().__init__(uuid)
        self.team_id = team_id
        self.name = name
        self.project_type = project_type
        self.description = description
        self.status = status
        self.folder_id = folder_id

    def to_dict(self):
        return {
            "id": self.uuid,
            "team_id": self.team_id,
            "name": self.name,
            "type": self.project_type,
            "description": self.description,
            "status": self.status,
        }


class FolderEntity(BaseEntity):
    def __init__(
        self,
        uuid: int = None,
        project_id: int = None,
        parent_id: int = None,
        team_id: int = None,
        name: str = None,
    ):
        super().__init__(uuid)
        self.team_id = team_id
        self.project_id = project_id
        self.name = name
        self.parent_id = parent_id

    def to_dict(self):
        return {
            "id": self.uuid,
            "team_id": self.team_id,
            "name": self.name,
            "parent_id": self.parent_id,
            "project_id": self.project_id,
        }
