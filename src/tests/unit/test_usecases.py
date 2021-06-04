from unittest import TestCase
from unittest.mock import Mock

from src.lib.core.usecases import BaseUseCase
from src.lib.core.exceptions import AppValidationException
from src.lib.core.response import Response


class TestBaseUseCase(TestCase):
    def setUp(self) -> None:
        self._response = Response()

        class UseCase(BaseUseCase):

            def execute(self):
                self.is_valid()

            def validate_test1(self):
                raise AppValidationException("Error 1")

            def validate_test2(self):
                raise AppValidationException("Error 2")

        self.use_case = UseCase(self._response)

    def test_validate_should_be_called(self):
        validate_method = Mock()
        self.use_case._validate = validate_method
        self.use_case.execute()
        validate_method.assert_called()

    def test_validate_should_fill_errors(self):
        self.use_case.execute()
        assert(len(self.use_case._errors) == 2)
