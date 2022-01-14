from superannotate_schemas.validators import AnnotationValidators
from unittest import TestCase


class TestPixelValidators(TestCase):

    def test_validate_annotation_invalid_hex(self):
        validator = AnnotationValidators.get_validator("pixel")(
            {
                "metadata": {
                    "name": "example_image_1.jpg",
                    "width": None,
                    "height": None,
                    "status": None,
                    "pinned": None,
                    "isPredicted": None,
                    "projectId": None,
                    "annotatorEmail": None,
                    "qaEmail": None,
                    "isSegmented": None
                },
                "instances": [
                    {
                        "classId": 56821,
                        "probability": 100,
                        "visible": True,
                        "attributes": [
                            {
                                "id": 57099,
                                "groupId": 21449,
                                "name": "no",
                                "groupName": "small"
                            }
                        ],
                        "parts": [
                            {
                                "color": [12,3]
                            }
                        ],
                        "error": None,
                        "className": "Large vehicle"
                    }
            ]
            }
        )
        self.assertFalse(validator.is_valid())
