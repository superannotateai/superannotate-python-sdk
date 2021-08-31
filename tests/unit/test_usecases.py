from unittest import TestCase
from unittest.mock import Mock

import pytest

from src.superannotate.lib.core.exceptions import AppValidationException
from src.superannotate.lib.core.usecases import BaseUseCase


@pytest.mark.skip(reason="Need to adjust")
class TestBaseUseCase(TestCase):
    def setUp(self) -> None:
        class UseCase(BaseUseCase):
            def execute(self):
                self.is_valid()
                return self._response

            def validate_test1(self):
                raise AppValidationException("Error 1")

            def validate_test2(self):
                raise AppValidationException("Error 2")

        self.use_case = UseCase()

    def test_validate_should_be_called(self):
        validate_method = Mock()
        self.use_case._validate = validate_method
        self.use_case.execute()
        validate_method.assert_called()

    def test_validate_should_fill_errors(self):
        print(self.use_case.execute().errors)
        assert len(self.use_case.execute().errors) == 2
