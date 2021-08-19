import os

import pytest
import src.superannotate as sa
from tests.integration.base import BaseTestCase


@pytest.mark.skipif(
    "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ,
    reason="Requires env variable to be set",
)
class TestUploadImageFromGoogleCloud(BaseTestCase):
    PROJECT_NAME = "test_google_cloud_upload"
    GOOGLE_PROJECT = "siam"
    BUCKET_NAME = "superannotate-python-sdk-tests"
    PROJECT_TYPE = "Vector"

    def test_upload_images_from_google_cloud_to_project(self):
        folder_path_with_test_imgs = "cat_pics_sdk_test"
        folder_path_empty = "empty_folder"
        folder_path_non_existent = "non_existent"
        test_folders = [
            (folder_path_with_test_imgs, [6, 0, 6, 0]),
            (folder_path_empty, [0, 0, 0, 0]),
            (folder_path_non_existent, [0, 0, 0, 0]),
        ]
        for folder_path, true_res in test_folders:
            (
                uploaded_urls,
                uploaded_filenames,
                duplicate_filenames,
                not_uploaded_urls,
            ) = sa.upload_images_from_google_cloud_to_project(
                self.PROJECT_NAME,
                self.GOOGLE_PROJECT,
                self.BUCKET_NAME,
                folder_path,
                annotation_status="InProgress",
                image_quality_in_editor="original",
            )
            self.assertEqual(len(uploaded_urls), true_res[0])
            self.assertEqual(len(duplicate_filenames), true_res[1])
            self.assertEqual(len(uploaded_filenames), true_res[2])
            self.assertEqual(len(not_uploaded_urls), true_res[3])
