from unittest import TestCase
from unittest.mock import patch

from src.superannotate import SAClient

sa = SAClient()


class TestVectorValidators(TestCase):
    PROJECT_TYPE = "Multimodal"

    @patch("builtins.print")
    def test_validate_annotation_without_metadata(self, mock_print):
        is_valid = sa.validate_annotations(self.PROJECT_TYPE, {"instances": []})
        assert not is_valid
        mock_print.assert_any_call("'metadata' is a required property")
