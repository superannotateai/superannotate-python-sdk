from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import List
from typing import Optional

from src.lib.core.conditions import Condition
from src.lib.core.entities import BaseEntity


class BaseReadOnlyRepository(ABC):
    @abstractmethod
    def get_one(self, uuid: Any) -> Optional[BaseEntity]:
        raise NotImplementedError

    @abstractmethod
    def get_all(self, condition: Optional[Condition] = None) -> List[BaseEntity]:
        raise NotImplementedError


class BaseManageableRepository(BaseReadOnlyRepository):
    @abstractmethod
    def insert(self, entity: BaseEntity) -> BaseEntity:
        raise NotImplementedError

    @abstractmethod
    def update(self, entity: BaseEntity):
        raise NotImplementedError

    @abstractmethod
    def delete(self, uuid: Any):
        raise NotImplementedError
