from src.superannotate import SAClient
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

    def test_get_project_by_id(self):
        project_metadata = sa.get_project_metadata(self.PROJECT_NAME)
        project_by_id = sa.get_project_by_id(project_metadata["id"])
        assert project_by_id["name"] == self.PROJECT_NAME
