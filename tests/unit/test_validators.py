import json
import os
from os.path import dirname
import tempfile

import src.superannotate as sa
from tests.utils.helpers import catch_prints
from src.superannotate.lib.infrastructure.validators import AnnotationValidator

from unittest import TestCase

VECTOR_ANNOTATION_JSON_WITH_BBOX = """
{
  "metadata": {
    "name": "example_image_1.jpg",
    "width": 1024,
    "height": 683,
    "status": "Completed",
    "pinned": false,
    "isPredicted": null,
    "projectId": null,
    "annotatorEmail": null,
    "qaEmail": null
  },
  "instances": [
    {
      "type": "bbox",
      "classId": 72274,
      "probability": 100,
      "points": {
        
        "x2": 465.23,
        "y1": 341.5,
        "y2": 357.09
      },
      "groupId": 0,
      "pointLabels": {},
      "locked": false,
      "visible": false,
      "attributes": [
        {
          "id": 117845,
          "groupId": 28230,
          "name": "2",
          "groupName": "Num doors"
        }
      ],
      "trackingId": "aaa97f80c9e54a5f2dc2e920fc92e5033d9af45b",
      "error": null,
      "createdAt": null,
      "createdBy": null,
      "creationType": null,
      "updatedAt": null,
      "updatedBy": null,
      "className": "Personal vehicle"
    }
  ]
}
"""


class TestValidators(TestCase):
    TEST_VECTOR_FOLDER_PATH = "data_set/sample_project_vector"
    VECTOR_JSON = "example_image_1.jpg___objects.json"

    @property
    def vector_folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_VECTOR_FOLDER_PATH)

    def test_validate_annotations_should_note_raise_errors(self):
        sa.validate_annotations("Vector", os.path.join(self.vector_folder_path, self.VECTOR_JSON))

    def test_validate_annotation_with_wrong_bbox(self):
        with tempfile.TemporaryDirectory() as tmpdir_name:
            with open(f"{tmpdir_name}/vector.json", "w") as vector_json:
                vector_json.write(VECTOR_ANNOTATION_JSON_WITH_BBOX)
            with catch_prints() as out:
                sa.validate_annotations("Vector", os.path.join(self.vector_folder_path, f"{tmpdir_name}/vector.json"))
                self.assertEqual("instances[0].points[x1]fieldrequired", out.getvalue().strip().replace(" ", ""))

    def test_validate_annotation_without_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir_name:
            with open(f"{tmpdir_name}/vector.json", "w") as vector_json:
                vector_json.write(
                    json.dumps({"instances": []})
                )
            with catch_prints() as out:
                sa.validate_annotations("Vector", os.path.join(self.vector_folder_path, f"{tmpdir_name}/vector.json"))
                self.assertIn("metadatafieldrequired", out.getvalue().strip().replace(" ", ""))

    def test_validate_annotation_invalid_date_time_format(self):
        data = """
            {
              "metadata": {
                "name": "example_image_1.jpg",
                "width": 1024,
                "height": 683,
                "status": "Completed",
                "pinned": false,
                "isPredicted": null,
                "projectId": null,
                "annotatorEmail": null,
                "qaEmail": null
              },
              "instances": [
                {
                  "type": "bbox",
                  "classId": 72274,
                  "probability": 100,
                  "points": {
                    "x1": 12,
                    "x2": 465.23,
                    "y1": 341.5,
                    "y2": 357.09
                  },
                  "groupId": 0,
                  "pointLabels": {},
                  "locked": false,
                  "visible": false,
                  "attributes": [
                    {
                      "id": 117845,
                      "groupId": 28230,
                      "name": "2",
                      "groupName": "Num doors"
                    }
                  ],
                  "trackingId": "aaa97f80c9e54a5f2dc2e920fc92e5033d9af45b",
                  "error": null,
                  "createdBy": null,
                  "creationType": null,
                  "updatedAt": "2021-11-02",
                  "updatedBy": null,
                  "className": "Personal vehicle"
                }
              ]
            }
            """
        validator = AnnotationValidator.get_vector_validator()(json.loads(data))
        validator.is_valid()
        self.assertIn("instances[0].updatedAtinvaliddatetimeformat", validator.generate_report().replace(" ", ""))

    def test_validate_annotation_valid_date_time_format(self):
        data = """
            {
              "metadata": {
                "name": "example_image_1.jpg",
                "width": 1024,
                "height": 683,
                "status": "Completed",
                "pinned": false,
                "isPredicted": null,
                "projectId": null,
                "annotatorEmail": null,
                "qaEmail": null
              },
              "instances": [
                {
                  "type": "bbox",
                  "classId": 72274,
                  "probability": 100,
                  "points": {
                    "x1": 12,
                    "x2": 465.23,
                    "y1": 341.5,
                    "y2": 357.09
                  },
                  "groupId": 0,
                  "pointLabels": {},
                  "locked": false,
                  "visible": false,
                  "attributes": [
                    {
                      "id": 117845,
                      "groupId": 28230,
                      "name": "2",
                      "groupName": "Num doors"
                    }
                  ],
                  "trackingId": "aaa97f80c9e54a5f2dc2e920fc92e5033d9af45b",
                  "error": null,
                  "createdBy": null,
                  "creationType": null,
                  "updatedAt": "2021-11-02T15:11:50.065Z",
                  "updatedBy": null,
                  "className": "Personal vehicle"
                }
              ]
            }
            """
        validator = AnnotationValidator.get_vector_validator()(json.loads(data))
        self.assertTrue(validator.is_valid())

    def test_validate_annotation_invalid_color_format(self):
        data = """
                    {
                      "metadata": {
                        "name": "example_image_1.jpg",
                        "width": null,
                        "height": null,
                        "status": null,
                        "pinned": null,
                        "isPredicted": null,
                        "projectId": null,
                        "annotatorEmail": null,
                        "qaEmail": null,
                        "isSegmented": null
                      },
                      "instances": [
                        {
                          "classId": 56821,
                          "probability": 100,
                          "visible": true,
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
                              "color": 132456324156321456
                            }
                          ],
                          "error": null,
                          "className": "Large vehicle"
                        }
                      ],
                      "tags": [],
                      "comments": []
                    }
                    """
        validator = AnnotationValidator.get_pixel_validator()(json.loads(data))
        validator.is_valid()
        self.assertIn("instances[0].parts[0].colorvalueisnotavalidcolor:stringnotrecognisedasavalidcolor", validator.generate_report().replace(" ", ""))

    def test_validate_annotation_valid_color_format(self):
        data = """
            {
              "metadata": {
                "name": "example_image_1.jpg",
                "width": null,
                "height": null,
                "status": null,
                "pinned": null,
                "isPredicted": null,
                "projectId": null,
                "annotatorEmail": null,
                "qaEmail": null,
                "isSegmented": null
              },
              "instances": [
                {
                  "classId": 56821,
                  "probability": 100,
                  "visible": true,
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
                      "color": "#000447"
                    }
                  ],
                  "error": null,
                  "className": "Large vehicle"
                }
              ],
              "tags": [],
              "comments": []
            }
            """
        validator = AnnotationValidator.get_pixel_validator()(json.loads(data))
        self.assertTrue(validator.is_valid())
