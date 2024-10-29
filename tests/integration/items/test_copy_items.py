import json
import os
import tempfile
from collections import Counter
from os.path import join
from pathlib import Path

from src.superannotate import AppException
from src.superannotate import SAClient
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestCopyItems(BaseTestCase):
    PROJECT_NAME = "TestCopyItemsVector"
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

    def test_copy_items_from_root(self):
        uploaded, _, _ = sa.attach_items(self.PROJECT_NAME, self.scv_path)
        assert len(uploaded) == 7
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_1)
        skipped_items = sa.copy_items(
            self.PROJECT_NAME, f"{self.PROJECT_NAME}/{self.FOLDER_1}"
        )
        assert len(skipped_items) == 0
        assert len(sa.search_items(f"{self.PROJECT_NAME}/{self.FOLDER_1}")) == 7

    def test_copy_items_from_root_with_annotations(self):
        uploaded, _, _ = sa.attach_items(self.PROJECT_NAME, self.ATTACHMENT)
        assert len(uploaded) == 2
        annotation_path = join(self.folder_path, f"{self.IMAGE_NAME}___objects.json")
        sa.upload_image_annotations(self.PROJECT_NAME, self.IMAGE_NAME, annotation_path)
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_1)
        skipped_items = sa.copy_items(
            self.PROJECT_NAME, f"{self.PROJECT_NAME}/{self.FOLDER_1}"
        )
        assert len(skipped_items) == 0
        assert len(sa.search_items(f"{self.PROJECT_NAME}/{self.FOLDER_1}")) == 2
        with tempfile.TemporaryDirectory() as tmp_dir:
            sa.download_image_annotations(
                f"{self.PROJECT_NAME}/{self.FOLDER_1}", self.IMAGE_NAME, tmp_dir
            )
            origin_annotation = json.load(open(annotation_path))
            annotation = json.load(open(join(tmp_dir, f"{self.IMAGE_NAME}.json")))
            self.assertEqual(
                len([i["attributes"] for i in annotation["instances"]]),
                len([i["attributes"] for i in origin_annotation["instances"]]),
            )

    def test_copy_items_from_not_existing_folder(self):
        with self.assertRaisesRegexp(AppException, "Folder not found."):
            sa.copy_items(f"{self.PROJECT_NAME}/{self.FOLDER_1}", self.PROJECT_NAME)

    def test_copy_items_to_not_existing_folder(self):
        with self.assertRaisesRegexp(AppException, "Folder not found."):
            sa.copy_items(self.PROJECT_NAME, f"{self.PROJECT_NAME}/{self.FOLDER_1}")

    def test_copy_items_from_folder(self):
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_1)
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_2)
        uploaded, _, _ = sa.attach_items(
            f"{self.PROJECT_NAME}/{self.FOLDER_1}", self.scv_path
        )
        assert len(uploaded) == 7
        skipped_items = sa.copy_items(
            f"{self.PROJECT_NAME}/{self.FOLDER_1}",
            f"{self.PROJECT_NAME}/{self.FOLDER_2}",
        )
        assert len(skipped_items) == 0
        assert len(sa.search_items(f"{self.PROJECT_NAME}/{self.FOLDER_2}")) == 7

    def test_skipped_count(self):
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_1)
        uploaded, _, _ = sa.attach_items(f"{self.PROJECT_NAME}", self.scv_path)
        _ = sa.copy_items(
            f"{self.PROJECT_NAME}", f"{self.PROJECT_NAME}/{self.FOLDER_1}"
        )
        skipped_items = sa.copy_items(
            f"{self.PROJECT_NAME}", f"{self.PROJECT_NAME}/{self.FOLDER_1}"
        )
        assert len(skipped_items) == 7

    def test_copy_items_wrong_items_list(self):
        uploaded, _, _ = sa.attach_items(
            self.PROJECT_NAME,
            self.ATTACHMENT,
        )
        sa.set_approval_statuses(self.PROJECT_NAME, "Approved", items=[self.IMAGE_NAME])
        sa.set_annotation_statuses(
            self.PROJECT_NAME, "Completed", items=[self.IMAGE_NAME]
        )
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_1)
        skipped_items = sa.copy_items(
            self.PROJECT_NAME,
            f"{self.PROJECT_NAME}/{self.FOLDER_1}",
            items=["as", "asd", self.IMAGE_NAME],
        )
        items = sa.search_items(f"{self.PROJECT_NAME}/{self.FOLDER_1}")
        assert len(items) == 1
        assert items[0]["name"] == self.IMAGE_NAME
        assert items[0]["annotation_status"] == "Completed"
        assert items[0]["approval_status"] == "Approved"
        assert Counter(skipped_items) == Counter(["as", "asd"])

    def test_copy_duplicated_items_without_data_with_replace_strategy(self):
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

        with self.assertLogs("sa", level="WARNING") as cm:
            skipped_items = sa.copy_items(
                f"{self.PROJECT_NAME}/{self.FOLDER_1}",
                f"{self.PROJECT_NAME}/{self.FOLDER_2}",
                include_annotations=False,
                duplicate_strategy="replace",
            )
            assert (
                "WARNING:sa:Copy operation continuing without annotations and metadata"
                " due to include_annotations=False." == cm.output[0]
            )
        assert len(skipped_items) == 2
        folder_1_items = sa.search_items(f"{self.PROJECT_NAME}/{self.FOLDER_1}")
        folder_2_items = sa.search_items(f"{self.PROJECT_NAME}/{self.FOLDER_2}")
        assert len(folder_1_items) == 2
        assert len(folder_2_items) == 2

        folder_2_items = sa.search_items(f"{self.PROJECT_NAME}/{self.FOLDER_2}")
        assert folder_2_items[0]["annotation_status"] == "NotStarted"
        assert not folder_2_items[0]["approval_status"]
