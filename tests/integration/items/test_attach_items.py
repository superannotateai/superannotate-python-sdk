import os
from pathlib import Path

from src.superannotate import SAClient
sa = SAClient()
from tests.integration.base import BaseTestCase


class TestAttachItemsVector(BaseTestCase):
    PROJECT_NAME = "TestAttachItemsVector"
    PROJECT_DESCRIPTION = "TestAttachItemsVector"
    PROJECT_TYPE = "Vector"
    FOLDER_NAME = "test_folder"
    CSV_PATH = "data_set/attach_urls.csv"
    PATH_TO_50K_URLS = "data_set/501_urls.csv"
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

    @property
    def scv_path_50k(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.PATH_TO_50K_URLS)

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

    def test_attach_items_to_folder(self):
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_NAME)
        uploaded, _, _ = sa.attach_items(f"{self.PROJECT_NAME}/{self.FOLDER_NAME}", self.ATTACHMENT_LIST)
        assert len(uploaded) == 3
        uploaded, _, duplicated = sa.attach_items(f"{self.PROJECT_NAME}/{self.FOLDER_NAME}", self.ATTACHMENT_LIST)
        assert len(uploaded) == 1
        assert len(duplicated) == 2

    def test_limitation(self):
        self.assertRaises(
            Exception,
            sa.attach_items,
            self.PROJECT_NAME,
            self.scv_path_50k
        )
