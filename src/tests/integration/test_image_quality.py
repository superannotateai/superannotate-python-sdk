import filecmp
import os
import tempfile
import time
from os.path import dirname

import src.lib.app.superannotate as sa
from src.tests.integration.base import BaseTestCase


class TestImageQuality(BaseTestCase):
    PROJECT_NAME = "img_q"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PTH = "data_set"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    def test_image_quality_setting1(self):
        sa.upload_images_from_folder_to_project(
            project=self._project["name"], folder_path=self.folder_path
        )
        with tempfile.TemporaryDirectory() as tmpdirname:
            sa.download_image(
                self.PROJECT_NAME,
                "example_image_1.jpg",
                tmpdirname + "/",
                variant="lores",
            )
            assert not filecmp.cmp(
                tmpdirname + "/example_image_1.jpg___lores.jpg",
                self.folder_path + "/example_image_1.jpg",
                shallow=False,
            )

    def test_image_quality_setting2(self):
        with tempfile.TemporaryDirectory() as tmpdir_name:
            sa.set_project_default_image_quality_in_editor(
                self.PROJECT_NAME, "original"
            )
            time.sleep(2)
            sa.upload_images_from_folder_to_project(
                project=self.PROJECT_NAME, folder_path=self.folder_path
            )
            time.sleep(2)

            sa.download_image(
                self.PROJECT_NAME,
                "example_image_1.jpg",
                tmpdir_name + "/",
                variant="lores",
            )

            assert filecmp.cmp(
                tmpdir_name + "/example_image_1.jpg___lores.jpg",
                self.folder_path + "/example_image_1.jpg",
                shallow=False,
            )
