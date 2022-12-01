from src.superannotate import SAClient

from tests.integration.base import BaseTestCase

sa = SAClient()


class TestSubSets(BaseTestCase):
    PROJECT_NAME = "Test-TestSubSets"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    SUBSET_NAME = "SUBSET"

    def test_add_items_to_subset(self):
        item_names = [{"name": f"earth_mov_00{i}.jpg", "url": f"url_{i}"} for i in range(1, 6)]
        sa.attach_items(
            self.PROJECT_NAME,
            item_names  # noqa
        )
        subset_data = []
        for i in item_names:
            subset_data.append(
                {
                    "name": i['name'],
                    "path": self.PROJECT_NAME
                }
            )
        sa.add_items_to_subset(self.PROJECT_NAME, self.SUBSET_NAME, subset_data)
