from abc import ABC
from abc import ABCMeta
from abc import abstractmethod
from typing import Any
from typing import List
from typing import Optional
from typing import Union

import boto3
from lib.core.conditions import Condition
from lib.core.entities import BaseEntity
from lib.core.entities import ProjectEntity
from lib.core.serviceproviders import SuperannotateServiceProvider
from pydantic import BaseModel


class BaseReadOnlyRepository(ABC):
    @abstractmethod
    def get_one(self, uuid: Union[Condition, int]) -> Optional[Union[BaseModel]]:
        raise NotImplementedError

    @abstractmethod
    def get_all(self, condition: Optional[Condition] = None) -> List[Union[BaseModel]]:
        raise NotImplementedError

    @staticmethod
    def dict2entity(data: dict) -> BaseModel:
        raise NotImplementedError


class BaseManageableRepository(BaseReadOnlyRepository):
    @abstractmethod
    def insert(self, entity: BaseEntity) -> BaseEntity:
        raise NotImplementedError

    @abstractmethod
    def update(self, entity: BaseEntity) -> BaseEntity:
        raise NotImplementedError

    @abstractmethod
    def delete(self, uuid: Any):
        raise NotImplementedError

    def bulk_delete(self, entities: List[BaseEntity]) -> bool:
        raise NotImplementedError

    @staticmethod
    def _drop_nones(data: dict):
        for k, v in list(data.items()):
            if v is None:
                del data[k]
        return data


class BaseProjectRelatedManageableRepository(
    BaseManageableRepository, metaclass=ABCMeta
):
    def __init__(self, service: SuperannotateServiceProvider, project: ProjectEntity):
        self._service = service
        self._project = project


class BaseS3Repository(BaseManageableRepository):
    def __init__(
        self,
        access_key: str,
        secret_key: str,
        session_token: str,
        bucket: str,
    ):
        self._session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=session_token,
        )

        self._resource = self._session.resource("s3")
        self._bucket = bucket
        self.bucket = self._resource.Bucket(bucket)
