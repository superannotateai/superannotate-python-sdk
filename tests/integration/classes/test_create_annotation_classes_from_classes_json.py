import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import pytest
from src.superannotate import AppException
from src.superannotate import SAClient
from tests import DATA_SET_PATH
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestVectorCreateAnnotationClass(BaseTestCase):
    PROJECT_NAME = "TestCreateAnnotationClass"
    PROJECT_TYPE = "Vector"
    PROJECT_DESCRIPTION = "Example "
    TEST_LARGE_CLASSES_JSON = "large_classes_json.json"
    EXAMPLE_IMAGE_1 = "example_image_1.jpg"
    INVALID_CLASSES_JON_PATH = "data_set/invalid_json/classes.json"

    @property
    def large_json_path(self):
        return os.path.join(DATA_SET_PATH, self.TEST_LARGE_CLASSES_JSON)

    @property
    def invalid_classes_path(self):
        return os.path.join(
            Path(__file__).parent.parent.parent, self.INVALID_CLASSES_JON_PATH
        )

    @property
    def classes_json(self):
        return os.path.join(
            Path(__file__).parent.parent.parent,
            "data_set/sample_project_vector/classes/classes.json",
        )

    def test_create_annotation_class_from_json(self):
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.classes_json
        )
        self.assertEqual(len(sa.search_annotation_classes(self.PROJECT_NAME)), 4)

        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.classes_json
        )
        self.assertEqual(len(sa.search_annotation_classes(self.PROJECT_NAME)), 4)

    # TODO failed after SDK_core integration (check validation in future)
    def test_invalid_json(self):
        try:
            sa.create_annotation_classes_from_classes_json(
                self.PROJECT_NAME, self.invalid_classes_path
            )
        except Exception as e:
            self.assertIn("Couldn't validate annotation classes", str(e))

    def test_create_annotation_classes_from_s3(self):
        annotation_classes = sa.search_annotation_classes(self.PROJECT_NAME)
        self.assertEqual(len(annotation_classes), 0)
        f = urlparse("s3://superannotate-python-sdk-test/sample_project_pixel")

        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME,
            f.path[1:] + "/classes/classes.json",
            from_s3_bucket=f.netloc,
        )
        annotation_classes = sa.search_annotation_classes(self.PROJECT_NAME)
        self.assertEqual(len(annotation_classes), 5)


class TestVideoCreateAnnotationClasses(BaseTestCase):
    PROJECT_NAME = "TestVideoCreateAnnotationClasses"
    PROJECT_TYPE = "Video"
    PROJECT_DESCRIPTION = "Example Project test pixel basic images"

    @pytest.mark.skip(reason="Need to adjust")
    def test_create_annotation_class(self):
        with tempfile.TemporaryDirectory() as tmpdir_name:
            temp_path = f"{tmpdir_name}/new_classes.json"
            with open(temp_path, "w") as new_classes:
                new_classes.write(
                    """
                    [
                       {
                          "id":56820,
                          "project_id":7617,
                          "name":"Personal vehicle",
                          "color":"#547497",
                          "count":18,
                          "createdAt":"2020-09-29T10:39:39.000Z",
                          "updatedAt":"2020-09-29T10:48:18.000Z",
                          "type": "tag",
                          "attribute_groups":[
                             {
                                "id":21448,
                                "class_id":56820,
                                "name":"Large",
                                "createdAt":"2020-09-29T10:39:39.000Z",
                                "updatedAt":"2020-09-29T10:39:39.000Z",
                                "attributes":[]
                             }
                          ]
                       }
                    ]

                    """
                )
            msg = ""
            try:
                sa.create_annotation_classes_from_classes_json(
                    self.PROJECT_NAME, temp_path
                )
            except Exception as e:
                msg = str(e)
            self.assertEqual(
                msg,
                "Predefined tagging functionality is not supported for projects of type Video.",
            )

    # TODO failed after SDK_core integration (check validation in future)
    def test_create_annotation_class_via_json_and_ocr_group_type(self):
        with tempfile.TemporaryDirectory() as tmpdir_name:
            temp_path = f"{tmpdir_name}/new_classes.json"
            with open(temp_path, "w") as new_classes:
                new_classes.write(
                    """
                    [
                       {
                          "id":56820,
                          "project_id":7617,
                          "name":"Personal vehicle",
                          "color":"#547497",
                          "count":18,
                          "createdAt":"2020-09-29T10:39:39.000Z",
                          "updatedAt":"2020-09-29T10:48:18.000Z",
                          "type": "tag",
                          "attribute_groups":[
                             {
                                "id":21448,
                                "class_id":56820,
                                "name":"Large",
                                "group_type": "ocr",
                                "createdAt":"2020-09-29T10:39:39.000Z",
                                "updatedAt":"2020-09-29T10:39:39.000Z",
                                "attributes":[]
                             }
                          ]
                       }
                    ]
                    """
                )
            with self.assertRaisesRegexp(
                AppException,
                f"OCR attribute group is not supported for project type {self.PROJECT_TYPE}.",
            ):
                sa.create_annotation_classes_from_classes_json(
                    self.PROJECT_NAME, temp_path
                )

    def test_create_annotation_classes_with_empty_default_attribute(self):
        with tempfile.TemporaryDirectory() as tmpdir_name:
            temp_path = f"{tmpdir_name}/new_classes.json"
            with open(temp_path, "w") as new_classes:
                new_classes.write(
                    """
                    [
                       {
                          "id":56820,
                          "project_id":7617,
                          "name":"Personal vehicle",
                          "color":"#547497",
                          "count":18,
                          "type": "tag",
                          "attribute_groups":[
                             {
                                "id":21448,
                                "class_id":56820,
                                "name":"Large",
                                "group_type": "radio",
                                "attributes":[
                                    {"name": "Car"},
                                    {"name": "Track"},
                                    {"name": "Bus"}
                                ]
                             }
                          ]
                       }
                    ]
                    """
                )
            sa.create_annotation_classes_from_classes_json(
                self.PROJECT_NAME,
                classes_json=temp_path,
            )
        classes = sa.search_annotation_classes(self.PROJECT_NAME)
        assert classes[0]["attribute_groups"][0]["default_value"] is None


class TestPixelCreateAnnotationClass(BaseTestCase):
    PROJECT_NAME = "TestCreateAnnotationClassPixel"
    PROJECT_TYPE = "Pixel"
    PROJECT_DESCRIPTION = "Example "
    TEST_LARGE_CLASSES_JSON = "large_classes_json.json"

    @property
    def large_json_path(self):
        return os.path.join(DATA_SET_PATH, self.TEST_LARGE_CLASSES_JSON)

    # TODO failed after SDK_core integration (check validation in future)
    def test_create_annotation_classes_with_default_attribute(self):
        with self.assertRaisesRegexp(
            AppException,
            'The "default_value" key is not supported for project type Pixel.',
        ):
            with tempfile.TemporaryDirectory() as tmpdir_name:
                temp_path = f"{tmpdir_name}/new_classes.json"
                with open(temp_path, "w") as new_classes:
                    new_classes.write(
                        """
                        [
                           {
                              "id":56820,
                              "project_id":7617,
                              "name":"Personal vehicle",
                              "color":"#547497",
                              "count":18,
                              "type": "tag",
                              "attribute_groups":[
                                 {
                                    "id":21448,
                                    "class_id":56820,
                                    "name":"Large",
                                    "group_type": "radio",
                                    "attributes":[
                                        {"name": "Car"},
                                        {"name": "Track"},
                                        {"name": "Bus"}
                                    ],
                                    "default_value": "Bus"
                                 }
                              ]
                           }
                        ]
                        """
                    )
                sa.create_annotation_classes_from_classes_json(
                    self.PROJECT_NAME,
                    classes_json=temp_path,
                )
