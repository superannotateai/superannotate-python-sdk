from src.superannotate import SAClient
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestGetProjectMetadata(BaseTestCase):
    PROJECT_NAME = "TestGetProjectMetadata"
    PROJECT_TYPE = "Vector"
    PROJECT_DESCRIPTION = "DESCRIPTION"

    def test_metadata_payload(self):
        """
        checking item_count for project retrieve
        and exclude in list
        """
        project = sa.get_project_metadata(self.PROJECT_NAME)
        assert project['item_count'] == 0
        self._attach_items(count=5)
        sa.create_folder(self.PROJECT_NAME, "tmp")
        self._attach_items(count=5, folder="tmp")
        project = sa.get_project_metadata(self.PROJECT_NAME)
        assert project['item_count'] == 10
        projects = sa.search_projects(name=self.PROJECT_NAME, return_metadata=True)
        assert 'item_count' not in projects[0]
