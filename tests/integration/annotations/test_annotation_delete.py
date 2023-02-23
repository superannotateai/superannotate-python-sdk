import os
from pathlib import Path

import pytest
from src.superannotate import AppException
from src.superannotate import SAClient
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestAnnotationDelete(BaseTestCase):
    PROJECT_NAME = "TestAnnotationDelete"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_NAME = "folder"
    TEST_FOLDER_PATH = "data_set/sample_project_vector_single_image"
    EXAMPLE_IMAGE_1 = "example_image_1.jpg"
    EXAMPLE_IMAGE_2 = "example_image_2.jpg"

    @property
    def folder_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.TEST_FOLDER_PATH)

    @property
    def classes_json(self):
        return os.path.join(
            Path(__file__).parent.parent.parent,
            "data_set/sample_project_vector/classes/classes.json",
        )

    def test_delete_annotations(self):
        self._attach_items(count=1)
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.folder_path + "/classes/classes.json"
        )
        sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, f"{self.folder_path}"
        )
        sa.delete_annotations(self.PROJECT_NAME)
        annotations = sa.get_annotations(self.PROJECT_NAME, [self.EXAMPLE_IMAGE_1])
        del annotations[0]["metadata"]["projectId"]
        assert annotations == [
            {
                "metadata": {
                    "name": "example_image_1.jpg",
                    "height": None,
                    "width": None,
                    "isPredicted": False,
                    "status": "NotStarted",
                    "pinned": False,
                    "annotatorEmail": None,
                    "qaEmail": None,
                },
                "instances": [],
                "tags": [],
                "comments": [],
            }
        ]

    def test_delete_annotations_by_name(self):
        self._attach_items(count=1)
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.folder_path + "/classes/classes.json"
        )
        sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, f"{self.folder_path}"
        )
        sa.delete_annotations(self.PROJECT_NAME, [self.EXAMPLE_IMAGE_1])
        annotations = sa.get_annotations(self.PROJECT_NAME, [self.EXAMPLE_IMAGE_1])
        del annotations[0]["metadata"]["projectId"]
        assert annotations == [
            {
                "metadata": {
                    "name": "example_image_1.jpg",
                    "height": None,
                    "width": None,
                    "isPredicted": False,
                    "status": "NotStarted",
                    "pinned": False,
                    "annotatorEmail": None,
                    "qaEmail": None,
                },
                "instances": [],
                "tags": [],
                "comments": [],
            }
        ]

    def test_delete_annotations_by_not_existing_name(self):
        self._attach_items(count=1)
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.folder_path + "/classes/classes.json"
        )
        sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, f"{self.folder_path}"
        )
        with self.assertRaisesRegexp(
            AppException, "Invalid item names or empty folder."
        ):
            sa.delete_annotations(self.PROJECT_NAME, [self.EXAMPLE_IMAGE_2])

    @pytest.mark.flaky(reruns=2)
    def test_delete_annotations_wrong_path(self):
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME)
        self._attach_items(count=1, folder=self.TEST_FOLDER_NAME)
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.folder_path + "/classes/classes.json"
        )
        sa.upload_annotations_from_folder_to_project(
            f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME}", f"{self.folder_path}"
        )
        self.assertRaises(
            Exception, sa.delete_annotations, self.PROJECT_NAME, [self.EXAMPLE_IMAGE_1]
        )
