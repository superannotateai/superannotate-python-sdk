import os
import pytest
from os.path import dirname

import src.superannotate as sa
from tests.integration.base import BaseTestCase


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
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    @property
    def classes_json(self):
        return os.path.join(
            dirname(dirname(__file__)),
            "data_set/sample_project_vector/classes/classes.json",
        )

    @pytest.mark.skip(
        "waiting for deployment to dev",
    )
    def test_delete_annotations(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.folder_path + "/classes/classes.json"
        )
        sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, f"{self.folder_path}"
        )

        sa.delete_annotations(self.PROJECT_NAME)
        data = sa.get_image_annotations(self.PROJECT_NAME, self.EXAMPLE_IMAGE_1)
        self.assertIsNone(data["annotation_json"])
        self.assertIsNotNone(data["annotation_json_filename"])
        self.assertIsNone(data["annotation_mask"])

    @pytest.mark.skip(
        "waiting for deployment to dev",
    )
    def test_delete_annotations_by_not_existing_name(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.folder_path + "/classes/classes.json"
        )
        sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, f"{self.folder_path}"
        )
        self.assertRaises(Exception, sa.delete_annotations, self.PROJECT_NAME, [self.EXAMPLE_IMAGE_2])

