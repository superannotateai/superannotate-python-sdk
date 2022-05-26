import tempfile
from pathlib import Path
import os
import shutil
from os.path import join
import json
import pytest
from unittest.mock import patch
from unittest.mock import MagicMock

from src.superannotate import SAClient
sa = SAClient()
from tests.integration.base import BaseTestCase


class TestAnnotationUploadVectorWithoutClasses(BaseTestCase):
    PROJECT_NAME = "TestAnnotationUploadVectorWithoutClasses"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    S3_FOLDER_PATH = "sample_project_pixel"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    IMAGE_NAME = "example_image_1.jpg"

    @property
    def folder_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.TEST_FOLDER_PATH)

    @pytest.mark.flaky(reruns=3)
    @patch("lib.infrastructure.controller.Reporter", MagicMock())
    def test_annotation_upload(self):
        annotation_path = join(self.folder_path, f"{self.IMAGE_NAME}___objects.json")
        sa.upload_image_to_project(self.PROJECT_NAME, join(self.folder_path, self.IMAGE_NAME))
        dir_name = "tmp"
        with tempfile.TemporaryDirectory() as tmp_dir:
            shutil.copytree(self.folder_path, f"{tmp_dir}/{dir_name}")
            shutil.rmtree(f"{tmp_dir}/{dir_name}/classes")
            sa.upload_image_annotations(self.PROJECT_NAME, self.IMAGE_NAME, annotation_path)
            with tempfile.TemporaryDirectory() as classes_dir:
                classes_path = sa.download_annotation_classes_json(self.PROJECT_NAME, classes_dir)
                self.assertEqual(json.load(open(classes_path, "r")), [])
                sa.create_annotation_class(self.PROJECT_NAME, "tt", "#FFFFFF", class_type="tag")
                classes_path = sa.download_annotation_classes_json(self.PROJECT_NAME, classes_dir)
                classes_json = json.load(open(classes_path, "r"))
                self.assertEqual(classes_json[0]["type"], "tag")
