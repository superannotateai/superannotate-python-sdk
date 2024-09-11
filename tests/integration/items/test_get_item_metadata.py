import os
from pathlib import Path

from src.superannotate import SAClient
from tests import compare_result
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestGetEntityMetadataVector(BaseTestCase):
    PROJECT_NAME = "TestGetEntityMetadataVector"
    PROJECT_DESCRIPTION = "TestGetEntityMetadataVector"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    CSV_PATH = "data_set/attach_urls.csv"
    IMAGE_NAME = "example_image_1.jpg"
    ATTACHED_IMAGE_NAME = "6022a74d5384c50017c366b3"
    IGNORE_KEYS = {"id", "createdAt", "updatedAt"}
    EXPECTED_ITEM_METADATA = {
        "name": "example_image_1.jpg",
        "path": "TestGetEntityMetadataVector",
        "url": None,
        "annotator_email": None,
        "qa_email": None,
        "annotation_status": "InProgress",
        "entropy_value": None,
        "prediction_status": "NotStarted",
        "segmentation_status": None,
        "approval_status": None,
        "is_pinned": False,
        "assignments": [],
    }

    @property
    def folder_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.TEST_FOLDER_PATH)

    @property
    def scv_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.CSV_PATH)

    def test_get_item_metadata(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        item_metadata = sa.get_item_metadata(self.PROJECT_NAME, self.IMAGE_NAME)
        assert item_metadata["path"] == f"{self.PROJECT_NAME}"
        assert compare_result(
            item_metadata, self.EXPECTED_ITEM_METADATA, self.IGNORE_KEYS
        )

    def test_get_item_by_id(self):
        project_metadata = sa.get_project_metadata(self.PROJECT_NAME)
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        item_metadata = sa.get_item_metadata(self.PROJECT_NAME, self.IMAGE_NAME)
        item_by_id = sa.get_item_by_id(project_metadata["id"], item_metadata["id"])
        assert item_by_id["name"] == self.IMAGE_NAME


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
        assert item_metadata["path"] == f"{self.PROJECT_NAME}"
        assert item_metadata["annotation_status"] == "InProgress"


class TestGetEntityMetadataVideo(BaseTestCase):
    PROJECT_NAME = "TestGetEntityMetadataVideo"
    PROJECT_DESCRIPTION = "TestGetEntityMetadataVideo"
    PROJECT_TYPE = "Video"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    ITEM_NAME = "example_image_1.jpg"

    @property
    def folder_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.TEST_FOLDER_PATH)

    def test_get_item_metadata(self):
        sa.attach_items(
            self.PROJECT_NAME,
            [
                {
                    "url": "https://drive.google.com/uc?export=download&id=1vwfCpTzcjxoEA4hhDxqapPOVvLVeS7ZS",
                    "name": self.ITEM_NAME,
                }
            ],
        )
        item_metadata = sa.get_item_metadata(self.PROJECT_NAME, self.ITEM_NAME)
        assert item_metadata["path"] == f"{self.PROJECT_NAME}"
        assert "prediction_status" not in item_metadata
        assert "segmentation_status" not in item_metadata
