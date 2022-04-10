from superannotate_schemas.validators import AnnotationValidators
from unittest import TestCase


class TestDocumentValidators(TestCase):

    def test_validate_text_annotation(self):
        validator = AnnotationValidators.get_validator("document")(
            {
                "metadata": {
                    "name": "text_file_example_1",
                    "status": "Completed",
                    "url": "https://sa-public-files.s3.us-west-2.amazonaws.com/Text+project/text_file_example_1.txt",
                    "projectId": 160158,
                    "annotatorEmail": None,
                    "qaEmail": None,
                    "lastAction": {
                        "email": "shab.prog@gmail.com",
                        "timestamp": 1634899229953
                    }
                },
                "instances": [
                    {
                        "type": "entity",
                        "start": 253,
                        "end": 593,
                        "classId": 873208,
                        "createdAt": "2021-10-22T10:40:26.151Z",
                        "createdBy": {
                            "email": "shab.prog@gmail.com",
                            "role": "Admin"
                        },
                        "updatedAt": "2021-10-22T10:40:29.953Z",
                        "updatedBy": {
                            "email": "shab.prog@gmail.com",
                            "role": "Admin"
                        },
                        "attributes": [],
                        "creationType": "Manual",
                        "className": "vid"
                    }
                ],
                "tags": [
                    "vid"
                ],
                "freeText": ""
            }
        )
        self.assertTrue(validator.is_valid())
