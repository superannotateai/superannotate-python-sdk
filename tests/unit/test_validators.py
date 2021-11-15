import json
import os
from os.path import dirname
import tempfile
import src.superannotate as sa
from tests.utils.helpers import catch_prints
from src.superannotate.lib.core.entities.utils import TimedBaseModel
from src.superannotate.lib.core.entities.pixel import PixelAnnotationPart
from pydantic import ValidationError
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
                self.assertIn("instances[0].points.x1fieldrequired", out.getvalue().strip().replace(" ", ""))

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
        with self.assertRaisesRegexp(ValidationError,"does not match expected format YYYY-MM-DDTHH:MM:SS.fffZ"):
            TimedBaseModel(createdAt="2021-11-02T15:11:50.065000Z")

    def test_validate_annotation_valid_date_time_format(self):
        self.assertEqual(TimedBaseModel(createdAt="2021-11-02T15:11:50.065Z").created_at, "2021-11-02T15:11:50.065Z")

    def test_validate_annotation_invalid_color_format(self):
        with self.assertRaisesRegexp(ValidationError, "1 validation error for PixelAnnotationPart"):
            PixelAnnotationPart(color="fd435eraewf4rewf")


    def test_validate_annotation_valid_color_format(self):
        self.assertEqual(PixelAnnotationPart(color="#f1f2f3").color, "#f1f2f3")


class TestTypeHandling(TestCase):
    ANNOTATION = """
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
          "type": "invalid_type",
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

    TEST_VECTOR_FOLDER_PATH = "data_set/sample_project_vector"
    VECTOR_JSON = "example_image_1.jpg___objects.json"

    @property
    def vector_folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_VECTOR_FOLDER_PATH)

    def test_validate_annotation_with_wrong_bbox(self):
        with tempfile.TemporaryDirectory() as tmpdir_name:
            with open(f"{tmpdir_name}/vector.json", "w") as vector_json:
                vector_json.write(self.ANNOTATION)
            with catch_prints() as out:
                sa.validate_annotations("Vector", os.path.join(self.vector_folder_path, f"{tmpdir_name}/vector.json"))
                self.assertEqual(
                    "instances[0]invalidtype,validtypesisbbox,"
                    "template,cuboid,polygon,point,polyline,ellipse,rbbox",
                    out.getvalue().strip().replace(" ", "")
                )

    def test_validate_document_annotation(self):
        with tempfile.TemporaryDirectory() as tmpdir_name:
            with open(f"{tmpdir_name}/doc.json", "w") as doc_json:
                doc_json.write(
                    '''
                    {
                        "metadata": {
                            "name": "text_file_example_1",
                            "status": "NotStarted",
                            "url": "https://sa-public-files.s3.us-west-2.amazonaws.com/Text+project/text_file_example_1.txt",
                            "projectId": 167826,
                            "annotatorEmail": null,
                            "qaEmail": null,
                            "lastAction": {
                                "email": "some.email@gmail.com",
                                "timestamp": 1636620976450
                            }
                        },
                        "instances": [],
                        "tags": [],
                        "freeText": ""
                    }
                    '''
                )
            self.assertTrue(sa.validate_annotations("Document", os.path.join(self.vector_folder_path, f"{tmpdir_name}/doc.json")))


    def test_validate_pixel_annotation(self):
        with tempfile.TemporaryDirectory() as tmpdir_name:
            with open(f"{tmpdir_name}/pixel.json", "w") as pix_json:
                pix_json.write(
                    '''
                    {
                    "metadata": {
                        "lastAction": {
                            "email": "some.email@gmail.com",
                            "timestamp": 1636627539398
                        },
                        "width": 1024,
                        "height": 683,
                        "name": "example_image_1.jpg",
                        "projectId": 164324,
                        "isPredicted": false,
                        "isSegmented": false,
                        "status": "NotStarted",
                        "pinned": false,
                        "annotatorEmail": null,
                        "qaEmail": null
                    },
                    "comments": [],
                    "tags": [],
                    "instances": []
                    }
                    '''
                )
            self.assertTrue(sa.validate_annotations("Pixel", os.path.join(self.vector_folder_path, f"{tmpdir_name}/pixel.json")))

    def test_validate_video_export_annotation(self):
        with tempfile.TemporaryDirectory() as tmpdir_name:
            with open(f"{tmpdir_name}/video_export.json", "w") as video_export:
                video_export.write(
                    '''
                    {
                        "metadata": {
                            "name": "video.mp4",
                            "width": 848,
                            "height": 476,
                            "status": "NotStarted",
                            "url": "https://file-examples-com.github.io/uploads/2017/04/file_example_MP4_480_1_5MG.mp4",
                            "duration": 2817000,
                            "projectId": 164334,
                            "error": null,
                            "annotatorEmail": null,
                            "qaEmail": null,
                            "lastAction": {
                                "timestamp": 1636384061135,
                                "email": "some.email@gmail.com"
                            }
                        },
                        "instances": [],
                        "tags": []
                    }
                    '''
                )
            self.assertTrue(sa.validate_annotations("Video", os.path.join(self.vector_folder_path,
                                                                          f"{tmpdir_name}/video_export.json")))


    def test_validate_vector_empty_annotation(self):
        with tempfile.TemporaryDirectory() as tmpdir_name:
            with open(f"{tmpdir_name}/vector_empty.json", "w") as vector_empty:
                vector_empty.write(
                    '''
                    {
                        "metadata": {
                            "lastAction": {
                                "email": "some.email@gmail.com",
                                "timestamp": 1636627956948
                            },
                            "width": 1024,
                            "height": 683,
                            "name": "example_image_1.jpg",
                            "projectId": 162462,
                            "isPredicted": false,
                            "status": "NotStarted",
                            "pinned": false,
                            "annotatorEmail": null,
                            "qaEmail": null
                        },
                        "comments": [],
                        "tags": [],
                        "instances": []
                    }
                    '''
                )
            self.assertTrue(sa.validate_annotations("Vector", os.path.join(self.vector_folder_path,
                                                                          f"{tmpdir_name}/vector_empty.json")))

    def test_validate_error_message_format(self):
        with tempfile.TemporaryDirectory() as tmpdir_name:
            with open(f"{tmpdir_name}/test_validate_error_message_format.json", "w") as test_validate_error_message_format:
                test_validate_error_message_format.write(
                    '''
                    {
                        "metadata": {}
                    }
                    '''
                )
            with catch_prints() as out:
                sa.validate_annotations("Vector", os.path.join(self.vector_folder_path,
                                                               f"{tmpdir_name}/test_validate_error_message_format.json"))
                self.assertIn("metadata.namefieldrequired", out.getvalue().strip().replace(" ", ""))


    def test_validate_document_annotation_wrong_class_id(self):
        with tempfile.TemporaryDirectory() as tmpdir_name:
            with open(f"{tmpdir_name}/test_validate_document_annotation_wrong_class_id.json", "w") as test_validate_document_annotation_wrong_class_id:
                test_validate_document_annotation_wrong_class_id.write(
                    '''
                    {
                        "metadata": {
                            "name": "text_file_example_1",
                            "status": "NotStarted",
                            "url": "https://sa-public-files.s3.us-west-2.amazonaws.com/Text+project/text_file_example_1.txt",
                            "projectId": 167826,
                            "annotatorEmail": null,
                            "qaEmail": null,
                            "lastAction": {
                                "email": "some.email@gmail.com",
                                "timestamp": 1636620976450
                            }
                        },
                        "instances": [{
                                      "start": 253,
                                      "end": 593,
                                      "classId": "string",
                                      "createdAt": "2021-10-22T10:40:26.151Z",
                                      "createdBy": {
                                        "email": "some.email@gmail.com",
                                        "role": "Admin"
                                      },
                                      "updatedAt": "2021-10-22T10:40:29.953Z",
                                      "updatedBy": {
                                        "email": "some.email@gmail.com",
                                        "role": "Admin"
                                      },
                                      "attributes": [],
                                      "creationType": "Manual",
                                      "className": "vid"
                                    }],
                        "tags": [],
                        "freeText": ""
                    }
                    '''
                )
            with catch_prints() as out:
                sa.validate_annotations("Document", os.path.join(self.vector_folder_path, f"{tmpdir_name}/test_validate_document_annotation_wrong_class_id.json"))
                self.assertIn("instances[0].classIdintegertypeexpected", out.getvalue().strip().replace(" ", ""))


    def test_validate_document_annotation_with_null_created_at(self):
        with tempfile.TemporaryDirectory() as tmpdir_name:
            with open(f"{tmpdir_name}/test_validate_document_annotation_with_null_created_at.json", "w") as test_validate_document_annotation_with_null_created_at:
                test_validate_document_annotation_with_null_created_at.write(
                    '''
                    {
                        "metadata": {
                            "name": "text_file_example_1",
                            "status": "NotStarted",
                            "url": "https://sa-public-files.s3.us-west-2.amazonaws.com/Text+project/text_file_example_1.txt",
                            "projectId": 167826,
                            "annotatorEmail": null,
                            "qaEmail": null,
                            "lastAction": {
                                "email": "some.email@gmail.com",
                                "timestamp": 1636620976450
                            }
                        },
                        "instances": [{
                                      "start": 253,
                                      "end": 593,
                                      "classId": 1,
                                      "createdAt": null,
                                      "createdBy": {
                                        "email": "some.email@gmail.com",
                                        "role": "Admin"
                                      },
                                      "updatedAt": null,
                                      "updatedBy": {
                                        "email": "some.email@gmail.com",
                                        "role": "Admin"
                                      },
                                      "attributes": [],
                                      "creationType": "Manual",
                                      "className": "vid"
                                    }],
                        "tags": [],
                        "freeText": ""
                    }
                    '''
                )
            self.assertTrue(sa.validate_annotations("Document", os.path.join(self.vector_folder_path,
                                                                             f"{tmpdir_name}/test_validate_document_annotation_with_null_created_at.json")))

