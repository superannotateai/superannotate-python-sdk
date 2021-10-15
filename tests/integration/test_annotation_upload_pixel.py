import os
from os.path import dirname
import pytest
import src.superannotate as sa
from tests.integration.base import BaseTestCase
import tempfile
import json
from os.path import join

class TestRecursiveFolderPixel(BaseTestCase):
    PROJECT_NAME = "test_recursive_pixel"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Pixel"
    S3_FOLDER_PATH = "sample_project_pixel"
    TEST_FOLDER_PATH = "data_set/sample_project_pixel"
    IMAGE_NAME = "example_image_1.jpg"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    @pytest.mark.flaky(reruns=2)
    def test_recursive_annotation_upload_pixel(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, recursive_subfolders=False
        )
        uploaded_annotations, _, _ = sa.upload_annotations_from_folder_to_project(self.PROJECT_NAME, self.S3_FOLDER_PATH,
                                                                from_s3_bucket="superannotate-python-sdk-test",
                                                                recursive_subfolders=False)
        self.assertEqual(len(uploaded_annotations), 3)

    @pytest.mark.flaky(reruns=2)
    def test_annotation_upload_pixel(self):
        sa.upload_images_from_folder_to_project(self.PROJECT_NAME, self.folder_path)
        sa.upload_annotations_from_folder_to_project(self.PROJECT_NAME, self.folder_path)
        with tempfile.TemporaryDirectory() as tmp_dir:
            sa.download_image_annotations(self.PROJECT_NAME, self.IMAGE_NAME, tmp_dir)
            origin_annotation = json.load(open(f"{self.folder_path}/{self.IMAGE_NAME}___pixel.json"))
            annotation = json.load(open(join(tmp_dir, f"{self.IMAGE_NAME}___pixel.json")))
            self.assertEqual(
                [i["attributes"] for i in annotation["instances"]],
                [i["attributes"] for i in origin_annotation["instances"]]
            )
