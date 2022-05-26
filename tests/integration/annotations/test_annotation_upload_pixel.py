import os
from os.path import join
from pathlib import Path
from unittest.mock import patch

from src.superannotate import SAClient
sa = SAClient()
from tests.integration.base import BaseTestCase

import pytest


class TestRecursiveFolderPixel(BaseTestCase):
    PROJECT_NAME = "test_recursive_pixel"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Pixel"
    S3_FOLDER_PATH = "sample_project_pixel"
    TEST_FOLDER_PATH = "data_set/sample_project_pixel"
    IMAGE_NAME = "example_image_1.jpg"
    FOLDER = "f"

    @pytest.fixture(autouse=True)
    def inject_fixtures(self, caplog):
        self._caplog = caplog

    @property
    def folder_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.TEST_FOLDER_PATH)

    @pytest.mark.flaky(reruns=4)
    @patch("lib.core.usecases.annotations.UploadAnnotationUseCase.s3_bucket")
    def test_recursive_annotation_upload_pixel(self, s3_bucket):
        sa.create_folder(self.PROJECT_NAME, self.FOLDER)
        destination = f"{self.PROJECT_NAME}/{self.FOLDER}"
        sa.upload_images_from_folder_to_project(
            destination, self.folder_path, recursive_subfolders=False
        )
        uploaded_annotations, _, _ = sa.upload_annotations_from_folder_to_project(
            destination,
            self.S3_FOLDER_PATH,
            from_s3_bucket="superannotate-python-sdk-test",
            recursive_subfolders=False
        )
        self.assertEqual(len(uploaded_annotations), 2)
        self.assertEqual(len(s3_bucket.method_calls), 4)

        uploaded_annotations, _, _ = sa.upload_preannotations_from_folder_to_project(
            destination,
            self.S3_FOLDER_PATH,
            from_s3_bucket="superannotate-python-sdk-test",
            recursive_subfolders=False
        )
        self.assertEqual(len(s3_bucket.method_calls), 8)

    def test_hex_color_adding(self):
        sa.create_annotation_class(self.PROJECT_NAME, "test_add", color="#0000FF")
        classes = sa.search_annotation_classes(self.PROJECT_NAME, "test_add")
        assert classes[0]["color"] == "#0000FF"


class TestAnnotationUploadPixelSingle(BaseTestCase):
    PROJECT_NAME = "TestAnnotationUploadPixelSingle"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Pixel"
    S3_FOLDER_PATH = "sample_project_pixel"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    IMAGE_NAME = "example_image_1.jpg"
    TEST_FOLDER_PATH_PIXEL = "data_set/sample_project_pixel"

    @property
    def folder_path_pixel(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.TEST_FOLDER_PATH_PIXEL)

    @pytest.mark.flaky(reruns=2)
    @patch("lib.core.usecases.annotations.UploadAnnotationUseCase.s3_bucket")
    def test_annotation_upload_pixel(self, s3_bucket):
        annotation_path = join(self.folder_path_pixel, f"{self.IMAGE_NAME}___pixel.json")
        sa.upload_image_to_project(self.PROJECT_NAME, join(self.folder_path_pixel, self.IMAGE_NAME))
        sa.upload_image_annotations(self.PROJECT_NAME, self.IMAGE_NAME, annotation_path)
        self.assertEqual(len(s3_bucket.method_calls), 2)
