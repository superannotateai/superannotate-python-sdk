from superannotate_schemas.validators import AnnotationValidators


from unittest import TestCase


class TestVectorValidators(TestCase):

    def test_validate_annotation_without_metadata(self):
        validator = AnnotationValidators().get_validator("vector")({"instances": []})
        self.assertFalse(validator.is_valid())
        self.assertEqual(
            "metadata                                         field required",
            validator.generate_report()
        )

    def test_validate_annotation_with_invalid_metadata(self):
        validator = AnnotationValidators().get_validator("vector")({"metadata": {"name": 12}})
        self.assertFalse(validator.is_valid())
        self.assertEqual(
            "metadata.name                                    str type expected",
            validator.generate_report()
        )

    def test_validate_instances(self):
        validator = AnnotationValidators().get_validator("vector")(
            {
                "metadata": {"name": "12"},
                "instances": [{"type": "invalid_type"}, {"type": "bbox"}]
            }
        )

        self.assertFalse(validator.is_valid())
        self.assertEqual(
            "instances[0].type                                invalid type, valid types are bbox, "
            "template, cuboid, polygon, point, polyline, ellipse, rbbox, tag\n"
            "instances[1].points                              field required",
            validator.generate_report()
        )

