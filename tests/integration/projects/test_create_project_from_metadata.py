import src.superannotate as sa
from tests.integration.base import BaseTestCase


class TestProjectRename(BaseTestCase):
    PROJECT_NAME = "TestProjectRename"
    NEW_PROJECT_NAME = "NewTestProjectRename"
    NAME_TO_RENAME = "TestPr"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"

    def tearDown(self) -> None:
        projects = sa.search_projects(self.NEW_PROJECT_NAME, return_metadata=True)
        for project in projects:
            sa.delete_project(project)
        super().tearDown()

    def test_create_project_from_metadata(self):
        project = sa.get_project_metadata(self.PROJECT_NAME, include_settings=True, include_contributors=True)
        project["name"] = self.NEW_PROJECT_NAME
        project["instructions_link"] = "instructions_link"
        new_project = sa.create_project_from_metadata(project)
        assert new_project["instructions_link"] == "instructions_link"

