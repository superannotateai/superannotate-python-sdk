import os
from pathlib import Path

import src.superannotate as sa
from tests.integration.base import BaseTestCase

import pytest


class TestAttachItemsVector(BaseTestCase):
    PROJECT_NAME = "TestAttachItemsVector"
    PROJECT_DESCRIPTION = "TestAttachItemsVector"
    PROJECT_TYPE = "Video"
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

    @pytest.mark.parametrize('project_type', scope="class", params=["Vector", "Video"])
    def setUp(self, *args, **kwargs):
        self.PROJECT_NAME = kwargs.get("project_type", BaseTestCase.__class__.__name__)
        super().setUp(*args, **kwargs)

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
