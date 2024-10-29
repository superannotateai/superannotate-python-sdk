import json
import os
import tempfile
from os.path import join
from pathlib import Path

from src.superannotate import SAClient
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestMoveItems(BaseTestCase):
    PROJECT_NAME = "TestMoveItemsVector"
    PROJECT_DESCRIPTION = "TestCopyItemsVector"
    PROJECT_TYPE = "Vector"
    IMAGE_NAME = "example_image_1.jpg"
    IMAGE_NAME_2 = "example_image_2.jpg"
    FOLDER_1 = "folder_1"
    FOLDER_2 = "folder_2"
    CSV_PATH = "data_set/attach_urls.csv"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"

    ATTACHMENT = [
        {
            "url": "https://drive.google.com/uc?export=download&id=1vwfCpTzcjxoEA4hhDxqapPOVvLVeS7ZS",
            "name": IMAGE_NAME,
        },
        {
            "url": "https://drive.google.com/uc?export=download&id=1vwfCpTzcjxoEA4hhDxqapPOVvLVeS7Zw",
            "name": IMAGE_NAME_2,
        },
    ]

    @property
    def folder_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.TEST_FOLDER_PATH)

    @property
    def scv_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.CSV_PATH)

    def test_move_items_from_root(self):
        uploaded, _, _ = sa.attach_items(self.PROJECT_NAME, self.scv_path)
        assert len(uploaded) == 7
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_1)
        skipped_items = sa.move_items(
            self.PROJECT_NAME, f"{self.PROJECT_NAME}/{self.FOLDER_1}"
        )
        assert len(skipped_items) == 0
        assert len(sa.search_items(f"{self.PROJECT_NAME}/{self.FOLDER_1}")) == 7

    def test_move_items_from_folder(self):
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_1)
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_2)
        uploaded, _, _ = sa.attach_items(
            f"{self.PROJECT_NAME}/{self.FOLDER_1}", self.ATTACHMENT
        )
        annotation_path = join(self.folder_path, f"{self.IMAGE_NAME}___objects.json")
        sa.upload_image_annotations(
            f"{self.PROJECT_NAME}/{self.FOLDER_1}", self.IMAGE_NAME, annotation_path
        )

        assert len(uploaded) == 2
        skipped_items = sa.move_items(
            f"{self.PROJECT_NAME}/{self.FOLDER_1}",
            f"{self.PROJECT_NAME}/{self.FOLDER_2}",
        )
        assert len(skipped_items) == 0
        assert len(sa.search_items(f"{self.PROJECT_NAME}/{self.FOLDER_2}")) == 2
        assert len(sa.search_items(f"{self.PROJECT_NAME}/{self.FOLDER_1}")) == 0
        with tempfile.TemporaryDirectory() as tmp_dir:
            sa.download_image_annotations(
                f"{self.PROJECT_NAME}/{self.FOLDER_2}", self.IMAGE_NAME, tmp_dir
            )
            origin_annotation = json.load(open(annotation_path))
            annotation = json.load(open(join(tmp_dir, f"{self.IMAGE_NAME}.json")))
            self.assertEqual(
                len([i["attributes"] for i in annotation["instances"]]),
                len([i["attributes"] for i in origin_annotation["instances"]]),
            )

    def test_move_items_from_folder_with_replace(self):
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_1)
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_2)
        uploaded, _, _ = sa.attach_items(
            f"{self.PROJECT_NAME}/{self.FOLDER_1}", self.ATTACHMENT
        )
        assert len(uploaded) == 2
        sa.set_approval_statuses(
            f"{self.PROJECT_NAME}/{self.FOLDER_1}",
            "Approved",
            items=[self.IMAGE_NAME, self.IMAGE_NAME_2],
        )
        sa.set_annotation_statuses(
            f"{self.PROJECT_NAME}/{self.FOLDER_1}",
            "Completed",
            items=[self.IMAGE_NAME, self.IMAGE_NAME_2],
        )

        uploaded_2, _, _ = sa.attach_items(
            f"{self.PROJECT_NAME}/{self.FOLDER_2}", self.ATTACHMENT
        )
        assert len(uploaded_2) == 2
        folder_2_items = sa.search_items(f"{self.PROJECT_NAME}/{self.FOLDER_2}")
        assert folder_2_items[0]["annotation_status"] == "NotStarted"
        assert not folder_2_items[0]["approval_status"]

        skipped_items = sa.move_items(
            f"{self.PROJECT_NAME}/{self.FOLDER_1}",
            f"{self.PROJECT_NAME}/{self.FOLDER_2}",
            duplicate_strategy="replace",
        )
        assert len(skipped_items) == 0
        folder_1_items = sa.search_items(f"{self.PROJECT_NAME}/{self.FOLDER_1}")
        folder_2_items = sa.search_items(f"{self.PROJECT_NAME}/{self.FOLDER_2}")
        assert len(folder_1_items) == 0
        assert len(folder_2_items) == 2

        folder_2_items = sa.search_items(f"{self.PROJECT_NAME}/{self.FOLDER_2}")
        assert folder_2_items[0]["annotation_status"] == "Completed"
        assert folder_2_items[0]["approval_status"] == "Approved"

    def test_move_items_from_folder_with_replace_annotations_only(self):
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_1)
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_2)
        uploaded, _, _ = sa.attach_items(
            f"{self.PROJECT_NAME}/{self.FOLDER_1}", self.ATTACHMENT
        )
        assert len(uploaded) == 2
        sa.set_approval_statuses(
            f"{self.PROJECT_NAME}/{self.FOLDER_1}",
            "Approved",
            items=[self.IMAGE_NAME, self.IMAGE_NAME_2],
        )
        sa.set_annotation_statuses(
            f"{self.PROJECT_NAME}/{self.FOLDER_1}",
            "Completed",
            items=[self.IMAGE_NAME, self.IMAGE_NAME_2],
        )
        annotation_path = join(self.folder_path, f"{self.IMAGE_NAME}___objects.json")
        sa.upload_image_annotations(
            f"{self.PROJECT_NAME}/{self.FOLDER_1}", self.IMAGE_NAME, annotation_path
        )

        uploaded_2, _, _ = sa.attach_items(
            f"{self.PROJECT_NAME}/{self.FOLDER_2}", self.ATTACHMENT
        )
        assert len(uploaded_2) == 2
        folder_2_items = sa.search_items(f"{self.PROJECT_NAME}/{self.FOLDER_2}")
        assert folder_2_items[0]["annotation_status"] == "NotStarted"
        assert not folder_2_items[0]["approval_status"]

        skipped_items = sa.move_items(
            f"{self.PROJECT_NAME}/{self.FOLDER_1}",
            f"{self.PROJECT_NAME}/{self.FOLDER_2}",
            duplicate_strategy="replace_annotations_only",
        )
        assert len(skipped_items) == 0
        folder_1_items = sa.search_items(f"{self.PROJECT_NAME}/{self.FOLDER_1}")
        folder_2_items = sa.search_items(f"{self.PROJECT_NAME}/{self.FOLDER_2}")
        assert len(folder_1_items) == 0
        assert len(folder_2_items) == 2

        folder_2_items = sa.search_items(f"{self.PROJECT_NAME}/{self.FOLDER_2}")
        assert folder_2_items[0]["annotation_status"] == "NotStarted"
        assert not folder_2_items[0]["approval_status"]
        with tempfile.TemporaryDirectory() as tmp_dir:
            sa.download_image_annotations(
                f"{self.PROJECT_NAME}/{self.FOLDER_2}", self.IMAGE_NAME, tmp_dir
            )
            origin_annotation = json.load(open(annotation_path))
            annotation = json.load(open(join(tmp_dir, f"{self.IMAGE_NAME}.json")))
            self.assertEqual(
                len([i["attributes"] for i in annotation["instances"]]),
                len([i["attributes"] for i in origin_annotation["instances"]]),
            )

    def test_move_items_from_folder_with_skip(self):
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_1)
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_2)
        uploaded, _, _ = sa.attach_items(
            f"{self.PROJECT_NAME}/{self.FOLDER_1}", self.ATTACHMENT
        )
        assert len(uploaded) == 2

        uploaded_2, _, _ = sa.attach_items(
            f"{self.PROJECT_NAME}/{self.FOLDER_2}", self.ATTACHMENT
        )
        assert len(uploaded_2) == 2

        skipped_items = sa.move_items(
            f"{self.PROJECT_NAME}/{self.FOLDER_1}",
            f"{self.PROJECT_NAME}/{self.FOLDER_2}",
            duplicate_strategy="skip",
        )
        assert len(skipped_items) == 2
