import os
from os.path import dirname

import src.superannotate as sa
from src.superannotate import AppException
from src.superannotate.lib.core import ATTACHING_UPLOAD_STATE_ERROR
from src.superannotate.lib.core import UPLOADING_UPLOAD_STATE_ERROR
from tests.integration.base import BaseTestCase


class TestVectorUploadStateCode(BaseTestCase):
    PROJECT_NAME = "TestVectorUploadStateCode"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PATH = "data_set"
    TEST_IMAGES_PATH = "sample_project_vector"
    PATH_TO_URLS = "attach_urls.csv"
    PATH_TO_VIDEOS = "sample_videos"
    IMAGE_NAME = "example_image_1.jpg"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    @property
    def attachments(self):
        return os.path.join(dirname(dirname(__file__)), self.PATH_TO_URLS)

    def test_attach_wrong_upload_state(self):
        sa.upload_image_to_project(self.PROJECT_NAME,
                                   os.path.join(self.folder_path, self.TEST_IMAGES_PATH, self.IMAGE_NAME))
        with self.assertRaisesRegexp(AppException, ATTACHING_UPLOAD_STATE_ERROR):
            sa.attach_image_urls_to_project(self.PROJECT_NAME, os.path.join(self.folder_path, self.PATH_TO_URLS))

    def test_upload_images_wrong_upload_state(self):
        sa.attach_image_urls_to_project(self.PROJECT_NAME, os.path.join(self.folder_path, self.PATH_TO_URLS))
        with self.assertRaisesRegexp(AppException, UPLOADING_UPLOAD_STATE_ERROR):
            sa.upload_images_from_folder_to_project(
                self.PROJECT_NAME,
                os.path.join(self.folder_path, self.TEST_IMAGES_PATH)
            )

    def test_upload_image_wrong_upload_state(self):
        sa.attach_image_urls_to_project(self.PROJECT_NAME, os.path.join(self.folder_path, self.PATH_TO_URLS))
        with self.assertRaisesRegexp(AppException, UPLOADING_UPLOAD_STATE_ERROR):
            sa.upload_image_to_project(
                self.PROJECT_NAME,
                os.path.join(self.folder_path, self.TEST_IMAGES_PATH, self.IMAGE_NAME)
            )

    def test_videos_image_wrong_upload_state(self):
        sa.attach_image_urls_to_project(self.PROJECT_NAME, os.path.join(self.folder_path, self.PATH_TO_URLS))
        with self.assertRaisesRegexp(AppException, UPLOADING_UPLOAD_STATE_ERROR):
            sa.upload_videos_from_folder_to_project(
                self.PROJECT_NAME,
                os.path.join(self.folder_path, self.PATH_TO_VIDEOS)
            )