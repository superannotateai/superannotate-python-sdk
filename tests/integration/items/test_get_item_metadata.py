import os
from pathlib import Path

import src.superannotate as sa
from tests.integration.base import BaseTestCase


class TestGetEntityMetadataVector(BaseTestCase):
    PROJECT_NAME = "TestGetEntityMetadataVector"
    PROJECT_DESCRIPTION = "TestGetEntityMetadataVector"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    IMAGE_NAME = "example_image_1.jpg"

    @property
    def folder_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.TEST_FOLDER_PATH)

    def test_get_item_metadata(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        item_metadata = sa.get_item_metadata(self.PROJECT_NAME, self.IMAGE_NAME)
        assert item_metadata["path"] == f"{self.PROJECT_NAME}/{self.IMAGE_NAME}"
        assert item_metadata["prediction_status"] == "NotStarted"
        assert item_metadata["segmentation_status"] == "NotStarted"
        assert item_metadata["annotation_status"] == "InProgress"


class TestGetEntityMetadataPixel(BaseTestCase):
    PROJECT_NAME = "TestGetEntityMetadataPixel"
    PROJECT_DESCRIPTION = "TestGetEntityMetadataPixel"
    PROJECT_TYPE = "Pixel"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    IMAGE_NAME = "example_image_1.jpg"

    @property
    def folder_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.TEST_FOLDER_PATH)

    def test_get_item_metadata(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        item_metadata = sa.get_item_metadata(self.PROJECT_NAME, self.IMAGE_NAME)
        assert item_metadata["path"] == f"{self.PROJECT_NAME}/{self.IMAGE_NAME}"
        assert item_metadata["prediction_status"] == "NotStarted"
        assert item_metadata["segmentation_status"] == "NotStarted"
        assert item_metadata["annotation_status"] == "InProgress"


