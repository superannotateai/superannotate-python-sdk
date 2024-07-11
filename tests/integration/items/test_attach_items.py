import os
from pathlib import Path
from unittest import TestCase

import pytest
from src.superannotate import AppException
from src.superannotate import SAClient
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestAttachItemsVector(BaseTestCase):
    PROJECT_NAME = "TestAttachItemsVector"
    PROJECT_DESCRIPTION = "TestAttachItemsVector"
    PROJECT_TYPE = "Vector"
    FOLDER_NAME = "test_folder"
    CSV_PATH = "data_set/attach_urls.csv"
    CSV_PATH_WITH_INTEGRATIONS = "data_set/attach_urls_integration.csv"
    PATH_TO_50K_URLS = "data_set/501_urls.csv"
    ATTACHED_IMAGE_NAME = "6022a74d5384c50017c366b3"
    ATTACHMENT_LIST = [
        {
            "url": "https://drive.google.com/uc?export=download&id=1vwfCpTzcjxoEA4hhDxqapPOVvLVeS7ZS",
            "name": "6022a74d5384c50017c366b3",
        },
        {
            "url": "https://drive.google.com/uc?export=download&id=1geS2YtQiTYuiduEirKVYxBujHJaIWA3V",
            "name": "6022a74b5384c50017c366ad",
        },
        {"url": "1SfGcn9hdkVM35ZP0S93eStsE7Ti4GtHU", "path": "123"},
        {
            "url": "https://drive.google.com/uc?export=download&id=1geS2YtQiTYuiduEirKVYxBujHJaIWA3V",
            "name": "6022a74b5384c50017c366ad",
        },
    ]

    @property
    def scv_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.CSV_PATH)

    @property
    def integrations_scv_path(self):
        return os.path.join(
            Path(__file__).parent.parent.parent, self.CSV_PATH_WITH_INTEGRATIONS
        )

    @property
    def scv_path_50k(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.PATH_TO_50K_URLS)

    def test_attached_items_csv(self):
        uploaded, _, _ = sa.attach_items(self.PROJECT_NAME, self.scv_path)
        assert len(uploaded) == 7
        uploaded, _, duplicated = sa.attach_items(self.PROJECT_NAME, self.scv_path)
        assert len(uploaded) == 2
        assert len(duplicated) == 5

    @pytest.mark.skip(reason="Need to have a custom integrations")
    def test_attached_items_with_integration_csv(self):
        uploaded, _, _ = sa.attach_items(self.PROJECT_NAME, self.integrations_scv_path)
        assert len(uploaded) == 5

    def test_attached_items_list_of_dict(self):
        uploaded, _, _ = sa.attach_items(self.PROJECT_NAME, self.ATTACHMENT_LIST)
        assert len(uploaded) == 3
        uploaded, _, duplicated = sa.attach_items(
            self.PROJECT_NAME, self.ATTACHMENT_LIST
        )
        assert len(uploaded) == 1
        assert len(duplicated) == 2

    def test_attach_items_to_folder(self):
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_NAME)
        uploaded, _, _ = sa.attach_items(
            f"{self.PROJECT_NAME}/{self.FOLDER_NAME}", self.ATTACHMENT_LIST
        )
        assert len(uploaded) == 3
        uploaded, _, duplicated = sa.attach_items(
            f"{self.PROJECT_NAME}/{self.FOLDER_NAME}", self.ATTACHMENT_LIST
        )
        assert len(uploaded) == 1
        assert len(duplicated) == 2

    def test_limitation(self):
        self.assertRaises(
            Exception, sa.attach_items, self.PROJECT_NAME, self.scv_path_50k
        )


class TestAttachItemsVectorArguments(TestCase):
    PROJECT_NAME = "TestAttachItemsVectorArguments"

    def test_attach_items_invalid_payload(self):
        error_msg = [
            "attachments",
            "str type expected",
            "value is not a valid path",
            r"attachments\[0].url",
            "field required",
        ]
        pattern = r"(\s+)" + r"(\s+)".join(error_msg)
        with self.assertRaisesRegexp(AppException, pattern):
            sa.attach_items(self.PROJECT_NAME, [{"name": "name"}])


def test_attach_gen_ai():
    try:
        sa.delete_folders("TEST_LLM_SCV_CATEGORIES_UPLOAD", ["f1", "f2"])
    except Exception as e:
        print(e)
    sa.create_folder("TEST_LLM_SCV_CATEGORIES_UPLOAD", "f1")
    sa.create_folder("TEST_LLM_SCV_CATEGORIES_UPLOAD", "f2")
    csv_path = os.path.join(
        Path(__file__).parent.parent.parent, "data_set/attach_genai.csv"
    )
    sa.attach_items("TEST_LLM_SCV_CATEGORIES_UPLOAD/f1", csv_path)
    sa.attach_items(
        "TEST_LLM_SCV_CATEGORIES_UPLOAD/f2",
        [
            {
                "_item_name": "i_000017",
                "_item_category": "_item_category1",
                "slider": "",
                "checkbox": "",
                "radio": "",
                "approve": "",
                "rating": "",
                "component_id_0": "",
                "component_id_1": "",
                "component_id_2": "",
            },
            {
                "_item_name": "i_00008",
                "_item_category": "_item_category1",
                "slider": "",
                "checkbox": "",
                "radio": "",
                "approve": "",
                "rating": "",
                "component_id_0": "",
                "component_id_1": "",
                "component_id_2": "",
            },
            {
                "_item_name": "i_00004",
                "_item_category": "_item_category1",
                "slider": "",
                "checkbox": "",
                "radio": "",
                "approve": "",
                "rating": "",
                "component_id_0": "",
                "component_id_1": "",
                "component_id_2": "",
            },
            {
                "_item_name": "i_000013",
                "_item_category": "_item_category1",
                "slider": 23,
                "checkbox": ["Option 1", "Option 3"],
                "radio": ["Option 1"],
                "approve": 1,
                "rating": 4,
                "component_id_0": ["Option 2"],
                "component_id_1": "6",
                "component_id_2": ["Option 1"],
            },
            {
                "_item_name": "i_000022",
                "_item_category": "",
                "slider": "",
                "checkbox": "",
                "radio": "",
                "approve": "",
                "rating": "",
                "component_id_0": "",
                "component_id_1": "",
                "component_id_2": "",
            },
            {
                "_item_name": "i_00002",
                "_item_category": "_item_category1",
                "slider": "",
                "checkbox": "",
                "radio": "",
                "approve": "",
                "rating": "",
                "component_id_0": "",
                "component_id_1": "",
                "component_id_2": "",
            },
            {
                "_item_name": "i_000011",
                "_item_category": "_item_category2",
                "slider": "",
                "checkbox": "",
                "radio": "",
                "approve": "",
                "rating": "",
                "component_id_0": '["Option 2"]',
                "component_id_1": "6",
                "component_id_2": '["Option 1"]',
            },
            {
                "_item_name": "i_000020",
                "_item_category": "",
                "slider": "",
                "checkbox": "",
                "radio": "",
                "approve": "",
                "rating": "",
                "component_id_0": "",
                "component_id_1": "",
                "component_id_2": "",
            },
            {
                "_item_name": "i_000019",
                "_item_category": "",
                "slider": "",
                "checkbox": "",
                "radio": "",
                "approve": "",
                "rating": "",
                "component_id_0": "",
                "component_id_1": "",
                "component_id_2": "",
            },
            {
                "_item_name": "i_000015",
                "_item_category": "_item_category2",
                "slider": "",
                "checkbox": "",
                "radio": "",
                "approve": "",
                "rating": "",
                "component_id_0": '["Option 1"]',
                "component_id_1": "6",
                "component_id_2": '["Option 1"]',
            },
            {
                "_item_name": "i_00006",
                "_item_category": "_item_category2",
                "slider": "",
                "checkbox": "",
                "radio": "",
                "approve": "",
                "rating": "",
                "component_id_0": "",
                "component_id_1": "",
                "component_id_2": "",
            },
            {
                "_item_name": "i_000024",
                "_item_category": "_item_category2",
                "slider": "",
                "checkbox": "",
                "radio": "",
                "approve": "",
                "rating": "",
                "component_id_0": "",
                "component_id_1": "",
                "component_id_2": "",
            },
            {
                "_item_name": "i_00001",
                "_item_category": "_item_category2",
                "slider": "",
                "checkbox": "",
                "radio": "",
                "approve": "",
                "rating": "",
                "component_id_0": '["Option 2"]',
                "component_id_1": "6",
                "component_id_2": '["Option 2"]',
            },
            {
                "_item_name": "i_000010",
                "_item_category": "_item_category2",
                "slider": "",
                "checkbox": "",
                "radio": "",
                "approve": "",
                "rating": "",
                "component_id_0": '["Option 1"]',
                "component_id_1": "4",
                "component_id_2": '["Option 2"]',
            },
            {
                "_item_name": "i_00009",
                "_item_category": "_item_category3",
                "slider": "",
                "checkbox": "",
                "radio": "",
                "approve": "",
                "rating": "",
                "component_id_0": "",
                "component_id_1": "",
                "component_id_2": "",
            },
            {
                "_item_name": "i_000018",
                "_item_category": "_item_category3",
                "slider": "",
                "checkbox": "",
                "radio": "",
                "approve": "",
                "rating": "",
                "component_id_0": "",
                "component_id_1": "",
                "component_id_2": "",
            },
            {
                "_item_name": "i_000023",
                "_item_category": "_item_category3",
                "slider": "",
                "checkbox": "",
                "radio": "",
                "approve": "",
                "rating": "",
                "component_id_0": "",
                "component_id_1": "",
                "component_id_2": "",
            },
            {
                "_item_name": "i_000014",
                "_item_category": "_item_category3",
                "slider": "",
                "checkbox": "",
                "radio": "",
                "approve": "",
                "rating": "",
                "component_id_0": '["Option 1"]',
                "component_id_1": "6",
                "component_id_2": '["Option 3"]',
            },
            {
                "_item_name": "i_00005",
                "_item_category": "_item_category3",
                "slider": "",
                "checkbox": "",
                "radio": "",
                "approve": "",
                "rating": "",
                "component_id_0": "",
                "component_id_1": "",
                "component_id_2": "",
            },
            {
                "_item_name": "i_000021",
                "_item_category": "",
                "slider": "",
                "checkbox": "",
                "radio": "",
                "approve": "",
                "rating": "",
                "component_id_0": "",
                "component_id_1": "",
                "component_id_2": "",
            },
            {
                "_item_name": "i_000012",
                "_item_category": "_item_category3",
                "slider": "",
                "checkbox": "",
                "radio": "",
                "approve": "",
                "rating": "",
                "component_id_0": '["Option 1"]',
                "component_id_1": "6",
                "component_id_2": '["Option 3"]',
            },
            {
                "_item_name": "i_00003",
                "_item_category": "_item_category3",
                "slider": "",
                "checkbox": "",
                "radio": "",
                "approve": "",
                "rating": "",
                "component_id_0": "",
                "component_id_1": "",
                "component_id_2": "",
            },
            {
                "_item_name": "i_000025",
                "_item_category": "",
                "slider": "",
                "checkbox": "",
                "radio": "",
                "approve": "",
                "rating": "",
                "component_id_0": "",
                "component_id_1": "",
                "component_id_2": "",
            },
            {
                "_item_name": "i_00007",
                "_item_category": "",
                "slider": "",
                "checkbox": "",
                "radio": "",
                "approve": "",
                "rating": "",
                "component_id_0": "",
                "component_id_1": "",
                "component_id_2": "",
            },
            {
                "_item_name": "i_000016",
                "_item_category": "",
                "slider": "",
                "checkbox": "",
                "radio": "",
                "approve": "",
                "rating": "",
                "component_id_0": "",
                "component_id_1": "",
                "component_id_2": "",
            },
        ],
    )
