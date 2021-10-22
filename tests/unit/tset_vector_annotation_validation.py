from src.superannotate.lib.infrastructure.validators import AnnotationValidator
from tests.utils.helpers import catch_prints

from unittest import TestCase


class TestVectorValidators(TestCase):

    def test_validate_annotation_without_metadata(self):
        validator = AnnotationValidator.get_vector_validator()({"instances": []})
        self.assertFalse(validator.is_valid())
        self.assertEqual("metadatafieldrequired", validator.generate_report().strip().replace(" ", ""))

    def test_validate_annotation_with_invalid_metadata(self):
        validator = AnnotationValidator.get_vector_validator()({"metadata": {"name": 12}})
        self.assertFalse(validator.is_valid())
        self.assertEqual("metadata[name]strtypeexpected", validator.generate_report().strip().replace(" ", ""))

    def test_validate_instances(self):
        validator = AnnotationValidator.get_vector_validator()(
            {
                "metadata": {"name": "12"},
                "instances": [{"type": "invalid_type"}, {"type": "bbox"}]
            }
        )

        self.assertFalse(validator.is_valid())
        print(validator.generate_report())
        self.assertEqual("metadata[name]strtypeexpected", validator.generate_report().strip().replace(" ", ""))

