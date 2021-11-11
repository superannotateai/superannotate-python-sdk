import copy
from abc import ABCMeta
from abc import abstractmethod
from typing import Any
from typing import Type

from pydantic import BaseModel
from pydantic import Extra


class BaseValidator(metaclass=ABCMeta):
    MODEL: BaseModel()

    def __init__(self, data: Any, allow_extra: bool = True):
        self.data = data
        self._validation_output = None
        self._extra = Extra.allow if allow_extra else Extra.forbid

    @classmethod
    def validate(cls, data: Any, extra=True):
        return cls.MODEL(**data)

    def _validate(self):
        model = copy.deepcopy(self.MODEL)
        model.Config.extra = self._extra
        self.data = model(**self.data).dict(by_alias=True, exclude_none=True)

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
