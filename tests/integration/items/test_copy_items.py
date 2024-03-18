import os
from collections import Counter
from pathlib import Path

from src.superannotate import AppException
from src.superannotate import SAClient
from tests.integration.base import BaseTestCase

sa = SAClient()
print()
sa.set_item_coponnet_value(639042, 39565701, 'component_id_1', 'value_0')
class TestCopyItems(BaseTestCase):
    PROJECT_NAME = "TestCopyItemsVector"
    PROJECT_DESCRIPTION = "TestCopyItemsVector"
    PROJECT_TYPE = "Vector"
    IMAGE_NAME = "test_image"
    FOLDER_1 = "folder_1"
    FOLDER_2 = "folder_2"
    CSV_PATH = "data_set/attach_urls.csv"

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
            [
                {
                    "url": "https://drive.google.com/uc?export=download&id=1vwfCpTzcjxoEA4hhDxqapPOVvLVeS7ZS",
                    "name": self.IMAGE_NAME,
                }
            ],
        )
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_1)
        skipped_items = sa.copy_items(
            self.PROJECT_NAME,
            f"{self.PROJECT_NAME}/{self.FOLDER_1}",
            items=["as", "asd"],
        )
        assert Counter(skipped_items) == Counter(["as", "asd"])
        assert len(sa.search_items(f"{self.PROJECT_NAME}/{self.FOLDER_1}")) == 0
