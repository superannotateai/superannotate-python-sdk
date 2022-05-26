import filecmp
import os
import tempfile
from os.path import dirname
import pytest

from src.superannotate import SAClient
sa = SAClient()
from tests.integration.base import BaseTestCase
from src.superannotate import AppException


class TestImageQuality(BaseTestCase):
    PROJECT_NAME = "img quality"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PTH = "data_set"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    EXAMPLE_IMAGE_1 = "example_image_1.jpg"

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
                self.EXAMPLE_IMAGE_1,
                tmpdirname + "/",
                variant="lores",
            )
            assert not filecmp.cmp(
                tmpdirname + "/" + self.EXAMPLE_IMAGE_1 + "___lores.jpg",
                self.folder_path + "/" + self.EXAMPLE_IMAGE_1,
                shallow=False,
            )

    def test_image_quality_setting2(self):
        with tempfile.TemporaryDirectory() as tmpdir_name:
            sa.set_project_default_image_quality_in_editor(
                self.PROJECT_NAME, "original"
            )
            sa.upload_images_from_folder_to_project(
                project=self.PROJECT_NAME, folder_path=self.folder_path
            )

            sa.download_image(
                self.PROJECT_NAME,
                self.EXAMPLE_IMAGE_1,
                tmpdir_name + "/",
                variant="lores",
            )

            self.assertTrue(
                filecmp.cmp(
                    tmpdir_name + "/" + self.EXAMPLE_IMAGE_1 + "___lores.jpg",
                    self.folder_path + "/" + self.EXAMPLE_IMAGE_1,
                    shallow=False,
                )
            )



class TestPixelImageQuality(BaseTestCase):
    PROJECT_NAME = "pixel image q"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Pixel"
    TEST_FOLDER_PATH = "data_set/big_img"
    BIG_IMAGE = "big.jpg"
    MESSAGE = "Image resolution 44761088 too large. Max supported for resolution is 4000000"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    @pytest.mark.flaky(reruns=2)
    def test_big_image(self):
        try:
            sa.upload_image_to_project(self.PROJECT_NAME, f"{self.folder_path}/{self.BIG_IMAGE}")
        except AppException as e:
            self.assertEqual(str(e), self.MESSAGE)



class TestImageQualitySetting(BaseTestCase):
    PROJECT_NAME = "TestImageQualitySetting Test"
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
