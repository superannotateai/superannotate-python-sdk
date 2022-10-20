from abc import ABC
from abc import ABCMeta
from abc import abstractmethod
from typing import Iterable
from typing import List

from lib.core.exceptions import AppValidationException
from lib.core.reporter import Reporter
from lib.core.response import Response


class BaseUseCase(ABC):
    def __init__(self):
        self._response = Response()
        self._pass_validation = False

    @abstractmethod
    def execute(self) -> Response:
        raise NotImplementedError

    def _validate(self):
        for name in dir(self):
            try:
                if name.startswith("validate_"):
                    method = getattr(self, name)
                    method()
            except AppValidationException as e:
                self._response.errors = e

    def is_valid(self):
        if self._pass_validation:
            return True
        self._validate()
        return not self._response.errors


class BaseInteractiveUseCase(BaseUseCase):
    def __init__(self):
        super().__init__()
        self._validated = False

    def is_valid(self):
        if not self._validated:
            self._validate()
            self._validated = True
        return not self._response.errors

    @property
    def response(self):
        return self._response

    @property
    def data(self):
        return self.response.data

    @abstractmethod
    def execute(self) -> Iterable:
        raise NotImplementedError


class BaseReportableUseCase(BaseUseCase, metaclass=ABCMeta):
    def __init__(self, reporter: Reporter):
        super().__init__()
        self.reporter = reporter


class BaseUserBasedUseCase(BaseReportableUseCase, metaclass=ABCMeta):
    """
    class contain validation of unique emails
    """

    def __init__(self, reporter: Reporter, emails: List[str]):
        super().__init__(reporter)
        self._emails = emails
