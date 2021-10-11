import os
from os.path import dirname
import pytest

import src.superannotate as sa
from tests.integration.base import BaseTestCase


class TestPinImage(BaseTestCase):
    PROJECT_NAME = "TestPinImage"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PTH = "data_set"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    EXAMPLE_IMAGE = "example_image_1.jpg"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    @pytest.mark.flaky(reruns=2)
    def test_pin_image(self):
        sa.upload_images_from_folder_to_project(
            project=self.PROJECT_NAME, folder_path=self.folder_path
        )

        img_metadata0 = sa.get_image_metadata(self.PROJECT_NAME, self.EXAMPLE_IMAGE)
        assert img_metadata0["is_pinned"] == 0

        sa.pin_image(self.PROJECT_NAME, self.EXAMPLE_IMAGE)

        img_metadata = sa.get_image_metadata(self.PROJECT_NAME, self.EXAMPLE_IMAGE)
        assert img_metadata["is_pinned"] == 1

        sa.pin_image(self.PROJECT_NAME, "example_image_1.jpg", True)
        img_metadata = sa.get_image_metadata(self.PROJECT_NAME, self.EXAMPLE_IMAGE)
        assert img_metadata["is_pinned"] == 1

        sa.pin_image(self.PROJECT_NAME, self.EXAMPLE_IMAGE, False)

        img_metadata = sa.get_image_metadata(self.PROJECT_NAME, self.EXAMPLE_IMAGE)
        assert img_metadata["is_pinned"] == 0

        del img_metadata["updatedAt"]
        del img_metadata0["updatedAt"]

        assert img_metadata == img_metadata0

    def test_pin_image_in_folder(self):
        test_folder = "test_folder"
        sa.create_folder(self.PROJECT_NAME, test_folder)
        project_folder = self.PROJECT_NAME + "/" + test_folder

        sa.upload_images_from_folder_to_project(
            project=project_folder, folder_path=self.folder_path
        )

        img_metadata0 = sa.get_image_metadata(project_folder, self.EXAMPLE_IMAGE)
        assert img_metadata0["is_pinned"] == 0

        sa.pin_image(project_folder, self.EXAMPLE_IMAGE)

        img_metadata = sa.get_image_metadata(project_folder, self.EXAMPLE_IMAGE)
        assert img_metadata["is_pinned"] == 1

        sa.pin_image(project_folder, self.EXAMPLE_IMAGE, True)
        img_metadata = sa.get_image_metadata(project_folder, self.EXAMPLE_IMAGE)
        assert img_metadata["is_pinned"] == 1

        sa.pin_image(project_folder, self.EXAMPLE_IMAGE, False)

        img_metadata = sa.get_image_metadata(project_folder, self.EXAMPLE_IMAGE)
        assert img_metadata["is_pinned"] == 0

        del img_metadata["updatedAt"]
        del img_metadata0["updatedAt"]

        assert img_metadata == img_metadata0
