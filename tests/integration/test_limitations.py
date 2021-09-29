import filecmp
import os
import tempfile
from os.path import dirname
import pytest

import src.superannotate as sa
from tests.integration.base import BaseTestCase
from src.superannotate import AppException


class TestImageQuality(BaseTestCase):
    PROJECT_NAME = "Limitation Test"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PTH = "data_set"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    EXAMPLE_IMAGE_1 = "example_image_1.jpg"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    def test_image_quality_setting1(self):
        uploaded, _, __ = sa.upload_images_from_folder_to_project(
            project=self._project["name"], folder_path=self.folder_path
        )
        uploaded, _, __ = sa.upload_images_from_folder_to_project(
            project=self._project["name"], folder_path=os.path.join(dirname(dirname(__file__)), "data_set")
        )
