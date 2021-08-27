import os
from os.path import dirname

import src.superannotate as sa
from tests.integration.base import BaseTestCase


class TestDuplicateImage(BaseTestCase):
    PROJECT_NAME = "duplicate_image"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PTH = "data_set"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    @property
    def classes_path(self):
        return os.path.join(
            dirname(dirname(__file__)), self.TEST_FOLDER_PATH, "classes/classes.json"
        )

    def test_single_image_upload(self):
        (
            uploaded,
            could_not_upload,
            existing_images,
        ) = sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress",
        )
        self.assertEqual(len(uploaded), 4)
        self.assertEqual(len(could_not_upload), 0)
        self.assertEqual(len(existing_images), 0)

        (
            uploaded,
            could_not_upload,
            existing_images,
        ) = sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress",
        )
        self.assertEqual(len(uploaded), 0)
        self.assertEqual(len(could_not_upload), 0)
        self.assertEqual(len(existing_images), 8)

        uploaded, could_not_upload, existing_images = sa.upload_images_to_project(
            self.PROJECT_NAME, [f"{self.folder_path}/dd.jpg"]
        )

        self.assertEqual(len(uploaded), 0)
        self.assertEqual(len(could_not_upload), 1)
        self.assertEqual(len(existing_images), 0)
