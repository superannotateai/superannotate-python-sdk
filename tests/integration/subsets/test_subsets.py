from src.superannotate import SAClient
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestSubSets(BaseTestCase):
    PROJECT_NAME = "Test-TestSubSets"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    SUBSET_NAME = "SUBSET"

    def test_add_items_to_subset(self):
        item_names = [
            {"name": f"earth_mov_00{i}.jpg", "url": f"url_{i}"} for i in range(1, 6)
        ]
        sa.attach_items(self.PROJECT_NAME, item_names)  # noqa
        subset_data = []
        for i in item_names:
            subset_data.append({"name": i["name"], "path": self.PROJECT_NAME})
        result = sa.add_items_to_subset(
            self.PROJECT_NAME, self.SUBSET_NAME, subset_data
        )
        assert len(subset_data) == len(result["succeeded"])

    def test_add_to_subset_with_duplicates_items(self):
        with self.assertLogs("sa", level="INFO") as cm:
            sa.attach_items(
                self.PROJECT_NAME, [{"name": "earth_mov_001.jpg", "url": "url_1"}]
            )  # noqa
            item_metadata = sa.get_item_metadata(self.PROJECT_NAME, "earth_mov_001.jpg")
            subset_data = [
                {"name": "earth_mov_001.jpg", "path": self.PROJECT_NAME},
                {"id": item_metadata["id"]},
            ]
            result = sa.add_items_to_subset(
                self.PROJECT_NAME, self.SUBSET_NAME, subset_data
            )
            assert len(result["succeeded"]) == 1
            assert (
                "INFO:sa:Dropping duplicates. Found 1 / 2 unique items." == cm.output[2]
            )

    def test_add_items_to_subset_by_project_id(self):
        project_id = sa.get_project_metadata(self.PROJECT_NAME)["id"]
        item_names = [
            {"name": f"earth_mov_00{i}.jpg", "url": f"url_{i}"} for i in range(1, 4)
        ]
        sa.attach_items(self.PROJECT_NAME, item_names)
        subset_data = [
            {"name": i["name"], "path": self.PROJECT_NAME} for i in item_names
        ]
        result = sa.add_items_to_subset(project_id, self.SUBSET_NAME, subset_data)
        assert len(subset_data) == len(result["succeeded"])

    def test_get_subsets_by_project_id(self):
        project_id = sa.get_project_metadata(self.PROJECT_NAME)["id"]
        item_names = [{"name": "earth_mov_001.jpg", "url": "url_1"}]
        sa.attach_items(self.PROJECT_NAME, item_names)
        subset_data = [{"name": "earth_mov_001.jpg", "path": self.PROJECT_NAME}]
        sa.add_items_to_subset(self.PROJECT_NAME, self.SUBSET_NAME, subset_data)
        subsets = sa.get_subsets(project_id)
        assert self.SUBSET_NAME in [s["name"] for s in subsets]
