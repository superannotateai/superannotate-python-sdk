from unittest import TestCase
from unittest.mock import patch

from src.superannotate import SAClient

sa = SAClient()


class TestVectorValidators(TestCase):
    PROJECT_TYPE = "vector"

    @patch('builtins.print')
    def test_validate_annotation_without_metadata(self, mock_print):
        is_valid = sa.validate_annotations("vector", {"instances": []})
        assert not is_valid
        mock_print.assert_any_call('\'metadata\' is a required property')

    @patch('builtins.print')
    def test_validate_annotation_with_invalid_metadata(self, mock_print):
        is_valid = sa.validate_annotations("vector", {"metadata": {"name": 12}})
        assert not is_valid
        mock_print.assert_any_call("metadata.name                                   12 is not of type 'string'")

    @patch('builtins.print')
    def test_validate_instances(self, mock_print):
        is_valid = sa.validate_annotations(
            "vector",
            {
                "metadata": {"name": "12"},
                "instances": [{"type": "invalid_type"}, {"type": "bbox"}]
            }
        )
        assert not is_valid
        mock_print.assert_any_call(
            "instances[0]                                    invalid type\n"
            "instances[1]                                    'points' is a required property"
        )

    @patch('builtins.print')
    def test_validate_create_dby(self, mock_print):
        is_valid = sa.validate_annotations(
            "vector",
            {
                "metadata": {"name": "12"},
                "instances": [
                    {
                        "type": "bbox",
                        "created_by": {}
                     },
                    {"type": "bbox"}
                ]
            }
        )
        assert not is_valid
        mock_print.assert_any_call(
            "instances[0]                                    invalid type\n"
            "instances[1]                                    'points' is a required property"
        )
