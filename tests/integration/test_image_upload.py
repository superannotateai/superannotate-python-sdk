import io
import os
from os.path import dirname

from src.superannotate import SAClient
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestSingleImageUpload(BaseTestCase):
    PROJECT_NAME = "single_image_upload"
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
        sa.upload_image_to_project(
            self.PROJECT_NAME,
            self.folder_path + "/example_image_1.jpg",
            annotation_status="InProgress",
        )
        assert len(sa.search_items(self.PROJECT_NAME)) == 1

        with open(self.folder_path + "/example_image_1.jpg", "rb") as f:
            img = io.BytesIO(f.read())

        sa.upload_image_to_project(
            self.PROJECT_NAME, img, image_name="rr.jpg", annotation_status="InProgress"
        )

        assert len(sa.search_items(self.PROJECT_NAME)) == 2


class TestMultipleImageUpload(BaseTestCase):
    PROJECT_NAME = "test_multiple_image_upload"
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

    def test_multiple_image_upload(self):
        (uploaded, could_not_upload, existing_images,) = sa.upload_images_to_project(
            self.PROJECT_NAME,
            [
                f"{self.folder_path}/example_image_1.jpg",
                f"{self.folder_path}/example_image_2.jpg",
                f"{self.folder_path}/example_image_3.jpg",
                f"{self.folder_path}/example_image_4.jpg",
            ],
            annotation_status="InProgress",
        )
        self.assertEqual(len(uploaded), 4)
        self.assertEqual(len(could_not_upload), 0)
        self.assertEqual(len(existing_images), 0)

        (uploaded, could_not_upload, existing_images,) = sa.upload_images_to_project(
            self.PROJECT_NAME,
            [
                f"{self.folder_path}/example_image_1.jpg",
                f"{self.folder_path}/example_image_2.jpg",
                f"{self.folder_path}/example_image_3.jpg",
                f"{self.folder_path}/example_image_4.jpg",
            ],
            annotation_status="InProgress",
        )
        self.assertEqual(len(uploaded), 0)
        self.assertEqual(len(could_not_upload), 0)
        self.assertEqual(len(existing_images), 4)

        uploaded, could_not_upload, existing_images = sa.upload_images_to_project(
            self.PROJECT_NAME, [f"{self.folder_path}/dd.jpg"]
        )
        self.assertEqual(len(uploaded), 0)
        self.assertEqual(len(could_not_upload), 1)
        self.assertEqual(len(existing_images), 0)

    def test_multiple_image_upload_with_duplicates(self):
        (uploaded, could_not_upload, existing_images,) = sa.upload_images_to_project(
            self.PROJECT_NAME,
            [
                f"{self.folder_path}/example_image_1.jpg",
                f"{self.folder_path}/example_image_1.jpg",
                f"{self.folder_path}/example_image_1.jpg",
                f"{self.folder_path}/example_image_3.jpg",
                f"{self.folder_path}/example_image_4.jpg",
            ],
            annotation_status="InProgress",
        )
        self.assertEqual(len(uploaded), 3)
        self.assertEqual(len(could_not_upload), 0)
        self.assertEqual(len(existing_images), 2)
