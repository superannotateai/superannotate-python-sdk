import os
from os.path import dirname

import src.superannotate as sa
from tests.integration.base import BaseTestCase

class TestRecursiveFolderPixel(BaseTestCase):
    PROJECT_NAME = "test_recursive_pixel"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Pixel"
    S3_FOLDER_PATH = "sample_project_pixel"
    TEST_FOLDER_PATH = "data_set/sample_project_pixel"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    def test_recursive_annotation_upload_pixel(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, recursive_subfolders=False
        )
        uploaded_annotations,_,_ = sa.upload_annotations_from_folder_to_project(self.PROJECT_NAME, self.S3_FOLDER_PATH,
                                                                from_s3_bucket="superannotate-python-sdk-test",
                                                                recursive_subfolders=False)
        self.assertEqual(len(uploaded_annotations), 3)