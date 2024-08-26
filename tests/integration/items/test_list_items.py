import os
from pathlib import Path

import src.superannotate.lib.core as constances
from src.superannotate import SAClient
from tests.integration.base import BaseTestCase
from tests.integration.items import IMAGE_EXPECTED_KEYS

sa = SAClient()


class TestListItems(BaseTestCase):
    PROJECT_NAME = "TestSearchItems"
    PROJECT_DESCRIPTION = "TestSearchItems"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    IMAGE1_NAME = "example_image_1.jpg"
    IMAGE2_NAME = "example_image_2.jpg"

    @property
    def folder_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.TEST_FOLDER_PATH)

    def test_list_items(self):
        sa.attach_items(
            self.PROJECT_NAME, [{"name": str(i), "url": str(i)} for i in range(100)]
        )
        items = sa.list_items(self.PROJECT_NAME)
        assert len(items) == 100
