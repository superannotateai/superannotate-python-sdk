from src.superannotate import SAClient
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestProjectSearch(BaseTestCase):
    PROJECT_NAME = "TestProjectSearch"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    PROJECT_NAME_2 = "TestProjectSearch2"
    REPLACED_PROJECT_NAME = "TestProjectSearchReplaced"
    PROJECT_NAME_CONTAIN_SPECIAL_CHARACTER = "TestProjectName!@#$%+"

    def setUp(self, *args, **kwargs):
        self.tearDown()
        self._project = sa.create_project(
            self.PROJECT_NAME, self.PROJECT_DESCRIPTION, self.PROJECT_TYPE
        )
        self._project_2 = sa.create_project(
            self.PROJECT_NAME_2, self.PROJECT_DESCRIPTION, self.PROJECT_TYPE
        )

    def tearDown(self) -> None:
        projects = []
        projects.extend(sa.search_projects(self.PROJECT_NAME, return_metadata=True))
        projects.extend(
            sa.search_projects(self.REPLACED_PROJECT_NAME, return_metadata=True)
        )
        projects.extend(
            sa.search_projects(
                self.PROJECT_NAME_CONTAIN_SPECIAL_CHARACTER, return_metadata=True
            )
        )
        for project in projects:
            try:
                sa.delete_project(project)
            except Exception as _:
                pass

    def test_project_search(self):
        # search before rename
        result = sa.search_projects(self.PROJECT_NAME, return_metadata=True)
        assert len(result) == 2

        # search after rename
        sa.rename_project(self.PROJECT_NAME, self.REPLACED_PROJECT_NAME)
        meta = sa.get_project_metadata(self.REPLACED_PROJECT_NAME)
        self.assertEqual(meta["name"], self.REPLACED_PROJECT_NAME)
        result = sa.search_projects(self.REPLACED_PROJECT_NAME, return_metadata=True)
        assert len(result) == 1
        assert result[0]["name"] == self.REPLACED_PROJECT_NAME

    def test_project_search_special_character(self):
        sa.rename_project(
            self.PROJECT_NAME, self.PROJECT_NAME_CONTAIN_SPECIAL_CHARACTER
        )
        meta = sa.get_project_metadata(self.PROJECT_NAME_CONTAIN_SPECIAL_CHARACTER)
        self.assertEqual(meta["name"], self.PROJECT_NAME_CONTAIN_SPECIAL_CHARACTER)
        result = sa.search_projects("!@#$%+", return_metadata=True)
        assert len(result) == 1
        assert result[0]["name"] == self.PROJECT_NAME_CONTAIN_SPECIAL_CHARACTER
