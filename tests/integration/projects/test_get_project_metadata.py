from src.superannotate import SAClient
from tests import compare_result
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestGetProjectMetadata(BaseTestCase):
    PROJECT_NAME = "TestGetProjectMetadata"
    PROJECT_TYPE = "Vector"
    PROJECT_DESCRIPTION = "DESCRIPTION"
    IGNORE_KEYS = {"id", "creator_id", "team_id", "createdAt", "updatedAt"}
    EXPECTED_PROJECT_METADATA = {
        "name": "TestGetProjectMetadata",
        "type": "Vector",
        "description": "DESCRIPTION",
        "instructions_link": None,
        "entropy_status": 1,
        "sharing_status": None,
        "status": "NotStarted",
        "folder_id": None,
        "upload_state": "EXTERNAL",
        "users": [],
        "completed_items_count": None,
        "root_folder_completed_items_count": None,
    }

    def test_metadata_payload(self):
        """
        checking item_count for project retrieve
        and exclude in list
        """
        project = sa.get_project_metadata(self.PROJECT_NAME)
        assert project["item_count"] == 0
        self._attach_items(count=5)
        sa.create_folder(self.PROJECT_NAME, "tmp")
        self._attach_items(count=5, folder="tmp")
        project = sa.get_project_metadata(self.PROJECT_NAME)
        assert project["item_count"] == 10
        projects = sa.search_projects(name=self.PROJECT_NAME, return_metadata=True)
        assert "item_count" not in projects[0]
        assert compare_result(
            projects[0], self.EXPECTED_PROJECT_METADATA, self.IGNORE_KEYS
        )

    def test_get_project_by_id(self):
        project_metadata = sa.get_project_metadata(self.PROJECT_NAME)
        project_by_id = sa.get_project_by_id(project_metadata["id"])
        assert project_by_id["name"] == self.PROJECT_NAME
