import os
from os.path import dirname

from src.superannotate import SAClient
sa = SAClient()
from tests.integration.base import BaseTestCase


class TestUploadImages(BaseTestCase):
    PROJECT_NAME = "TestUploadImages"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PATH = "data_set"
    TEST_IMAGES_PATH = "sample_project_vector"
    PATH_TO_VIDEOS = "sample_videos"
    IMAGE_NAME = "example_image_1.jpg"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    def test_upload_images_with_empty_extensions_list(self):
        result = sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME,
            os.path.join(self.folder_path, self.TEST_IMAGES_PATH),
            extensions=[]
            )
        self.assertEqual(([], [], []), result)
