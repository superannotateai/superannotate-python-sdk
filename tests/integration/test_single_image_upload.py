import io
import os
from os.path import dirname

from src.superannotate import SAClient
sa = SAClient()
from tests.integration.base import BaseTestCase


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
