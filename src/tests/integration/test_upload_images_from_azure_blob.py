import os

import pytest
import src.lib.app.superannotate as sa
from src.tests.integration.base import BaseTestCase


@pytest.mark.skipif(
    "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ,
    reason="Requires env variable to be set",
)
class TestUploadImageFromAzureCloud(BaseTestCase):
    PROJECT_NAME = "test_azure_cloud_upload"
    GOOGLE_PROJECT = "siam"
    BUCKET_NAME = "superannotate-python-sdk-tests"
    PROJECT_TYPE = "Vector"
    CONTAINER_NAME = "superannotate-python-sdk-tests"

    def test_upload_images_from_azure_storage_to_project(self):
        folder_path_with_test_imgs = "cat_pics_sdk_test"
        folder_path_nested = "cat_pics_nested_test"
        folder_path_non_existent = "nonex"
        test_folders = [
            (folder_path_with_test_imgs, [6, 0, 6, 0]),
            (folder_path_nested, [0, 6, 0, 0]),
            (folder_path_non_existent, [0, 0, 0, 0]),
        ]
        for folder_path, true_res in test_folders:
            (
                uploaded_urls,
                uploaded_filenames,
                duplicate_filenames,
                not_uploaded_urls,
            ) = sa.upload_images_from_azure_blob_to_project(
                self.PROJECT_NAME,
                self.CONTAINER_NAME,
                folder_path,
                annotation_status="InProgress",
                image_quality_in_editor="original",
            )
            self.assertEqual(len(uploaded_urls), true_res[0])
            self.assertEqual(len(duplicate_filenames), true_res[1])
            self.assertEqual(len(uploaded_filenames), true_res[2])
            self.assertEqual(len(not_uploaded_urls), true_res[3])
