import os
from collections import Counter
from pathlib import Path

from src.superannotate import SAClient
sa = SAClient()
from tests.integration.base import BaseTestCase


class TestCopyItems(BaseTestCase):
    PROJECT_NAME = "TestCopyItemsVector"
    PROJECT_DESCRIPTION = "TestCopyItemsVector"
    PROJECT_TYPE = "Vector"
    IMAGE_NAME ="test_image"
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
        skipped_items = sa.copy_items(self.PROJECT_NAME, f"{self.PROJECT_NAME}/{self.FOLDER_1}")
        assert len(skipped_items) == 0
        assert len(sa.search_items(f"{self.PROJECT_NAME}/{self.FOLDER_1}")) == 7

    def test_copy_items_from_folder(self):
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_1)
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_2)
        uploaded, _, _ = sa.attach_items(f"{self.PROJECT_NAME}/{self.FOLDER_1}", self.scv_path)
        assert len(uploaded) == 7
        skipped_items = sa.copy_items(f"{self.PROJECT_NAME}/{self.FOLDER_1}", f"{self.PROJECT_NAME}/{self.FOLDER_2}")
        assert len(skipped_items) == 0
        assert len(sa.search_items(f"{self.PROJECT_NAME}/{self.FOLDER_2}")) == 7

    def test_skipped_count(self):
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_1)
        uploaded, _, _ = sa.attach_items(f"{self.PROJECT_NAME}", self.scv_path)
        _ = sa.copy_items(f"{self.PROJECT_NAME}", f"{self.PROJECT_NAME}/{self.FOLDER_1}")
        skipped_items = sa.copy_items(f"{self.PROJECT_NAME}", f"{self.PROJECT_NAME}/{self.FOLDER_1}")
        assert len(skipped_items) == 7

    def test_copy_item_with_annotations(self):
        uploaded, _, _ = sa.attach_items(
            self.PROJECT_NAME, [
                {"url": "https://drive.google.com/uc?export=download&id=1vwfCpTzcjxoEA4hhDxqapPOVvLVeS7ZS",
                 "name": self.IMAGE_NAME}
            ]
        )
        assert len(uploaded) == 1
        sa.create_annotation_class(self.PROJECT_NAME, "test_class", "#FF0000")
        sa.add_annotation_bbox_to_image(self.PROJECT_NAME, self.IMAGE_NAME, [1, 2, 3, 4], "test_class")
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_1)
        skipped_items = sa.copy_items(
            self.PROJECT_NAME, f"{self.PROJECT_NAME}/{self.FOLDER_1}", include_annotations=True
        )
        annotations = sa.get_annotations(f"{self.PROJECT_NAME}/{self.FOLDER_1}")
        assert len(annotations) == 1
        assert len(skipped_items) == 0
        assert len(sa.search_items(f"{self.PROJECT_NAME}/{self.FOLDER_1}")) == 1

    def test_copy_items_wrong_items_list(self):
        uploaded, _, _ = sa.attach_items(
            self.PROJECT_NAME, [
                {"url": "https://drive.google.com/uc?export=download&id=1vwfCpTzcjxoEA4hhDxqapPOVvLVeS7ZS",
                 "name": self.IMAGE_NAME}
            ]
        )
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_1)
        skipped_items = sa.copy_items(self.PROJECT_NAME, f"{self.PROJECT_NAME}/{self.FOLDER_1}", items=["as", "asd"])
        assert Counter(skipped_items) == Counter(["as", "asd"])
        assert len(sa.search_items(f"{self.PROJECT_NAME}/{self.FOLDER_1}")) == 0
