import os
from pathlib import Path

from src.superannotate import SAClient
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestListItems(BaseTestCase):
    PROJECT_NAME = "TestListItems"
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
        sa.set_approval_statuses(self.PROJECT_NAME, "Disapproved")
        items = sa.list_items(self.PROJECT_NAME, approval_status="Disapproved")
        assert len(items) == 100
        items = sa.list_items(self.PROJECT_NAME, approval_status="Approved")
        assert len(items) == 0
        items = sa.list_items(self.PROJECT_NAME, approval_status__in=["Approved", None])
        assert len(items) == 0
        items = sa.list_items(
            self.PROJECT_NAME, approval_status__in=["Disapproved", None]
        )
        assert len(items) == 100
