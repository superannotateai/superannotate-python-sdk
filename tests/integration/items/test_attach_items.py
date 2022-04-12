import os
from pathlib import Path

import src.superannotate as sa
from tests.integration.base import BaseTestCase

import pytest


class TestAttachItemsVector(BaseTestCase):
    PROJECT_NAME = "TestAttachItemsVector"
    PROJECT_DESCRIPTION = "TestAttachItemsVector"
    PROJECT_TYPE = "Vector"
    CSV_PATH = "data_set/attach_urls.csv"
    ATTACHED_IMAGE_NAME = "6022a74d5384c50017c366b3"
    ATTACHMENT_LIST = [
        {
            "url": "https://drive.google.com/uc?export=download&id=1vwfCpTzcjxoEA4hhDxqapPOVvLVeS7ZS",
            "name": "6022a74d5384c50017c366b3"
        },
        {
            "url": "https://drive.google.com/uc?export=download&id=1geS2YtQiTYuiduEirKVYxBujHJaIWA3V",
            "name": "6022a74b5384c50017c366ad"
        },
        {
            "url": "1SfGcn9hdkVM35ZP0S93eStsE7Ti4GtHU",
            "path": "123"
        },
        {
            "url": "https://drive.google.com/uc?export=download&id=1geS2YtQiTYuiduEirKVYxBujHJaIWA3V",
            "name": "6022a74b5384c50017c366ad"
        },
    ]

    @property
    def scv_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.CSV_PATH)

    def test_attached_items_csv(self):
        uploaded, _, _ = sa.attach_items(self.PROJECT_NAME, self.scv_path)
        assert len(uploaded) == 7
        uploaded, _, duplicated = sa.attach_items(self.PROJECT_NAME, self.scv_path)
        assert len(uploaded) == 2
        assert len(duplicated) == 5

    def test_attached_items_list_of_dict(self):
        uploaded, _, _ = sa.attach_items(self.PROJECT_NAME, self.ATTACHMENT_LIST)
        assert len(uploaded) == 3
        uploaded, _, duplicated = sa.attach_items(self.PROJECT_NAME, self.ATTACHMENT_LIST)
        assert len(uploaded) == 1
        assert len(duplicated) == 2


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