from abc import ABCMeta
from abc import abstractmethod
from typing import Any
from typing import Type


class BaseValidator(metaclass=ABCMeta):
    def __init__(self, data: Any):
        self._data = data
        self._validation_output = None

    @classmethod
    @abstractmethod
    def validate(cls, data: Any):
        raise NotImplementedError

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
