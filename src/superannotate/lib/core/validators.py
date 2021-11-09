from abc import ABCMeta
from abc import abstractmethod
from typing import Any
from typing import Type

from pydantic import BaseModel


class BaseValidator(metaclass=ABCMeta):
    MODEL: BaseModel()

    def __init__(self, data: Any):
        self.data = data
        self._validation_output = None

    @classmethod
    def validate(cls, data: Any):
        return cls.MODEL(**data)

    def _validate(self):
        self.data = self.validate(self.data).dict(by_alias=True, exclude_none=True)

    @abstractmethod
    def is_valid(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def generate_report(self) -> str:
        raise NotImplementedError


class BaseAnnotationValidator(metaclass=ABCMeta):
    @staticmethod
    @abstractmethod
    def get_pixel_validator() -> Type[BaseValidator]:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def get_vector_validator() -> Type[BaseValidator]:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def get_video_validator() -> Type[BaseValidator]:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def get_document_validator() -> Type[BaseValidator]:
        raise NotImplementedError
