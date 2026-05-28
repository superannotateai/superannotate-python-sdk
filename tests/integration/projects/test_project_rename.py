from src.superannotate import SAClient
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestProjectRename(BaseTestCase):
    PROJECT_NAME = "TestProjectRename"
    NAME_TO_RENAME = "TestPr"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    NEW_PROJECT_NAME = "new"
    REPLACED_PROJECT_NAME = "_ _ _ _ _ _ _ _ _ _"
    BAD_PROJECT_NAME = r'/ \ : * ? " “ < > |'  # noqa: w605

    def setUp(self, *args, **kwargs):
        self.tearDown()
        self._project = sa.create_project(
            self.PROJECT_NAME, self.PROJECT_DESCRIPTION, self.PROJECT_TYPE
        )

    def tearDown(self) -> None:
        projects = sa.list_projects(
            name__in=[
                self.PROJECT_NAME,
                self.NEW_PROJECT_NAME,
                self.REPLACED_PROJECT_NAME,
                self.NAME_TO_RENAME,
            ]
        )
        for project in projects:
            try:
                sa.delete_project(project=project["id"])
            except Exception as _:
                pass

    def test_project_rename(self):
        sa.rename_project(self.PROJECT_NAME, self.NEW_PROJECT_NAME)
        meta = sa.get_project_metadata(self.NEW_PROJECT_NAME)
        self.assertEqual(meta["name"], self.NEW_PROJECT_NAME)

    def test_rename_with_special_characters(self):
        sa.rename_project(self.PROJECT_NAME, self.BAD_PROJECT_NAME)
        sa.get_project_metadata(self.REPLACED_PROJECT_NAME)

    def test_rename_with_substring_of_an_existing_name(self):
        sa.rename_project(self.PROJECT_NAME, self.NAME_TO_RENAME)
        metadata = sa.get_project_metadata(self.NAME_TO_RENAME)
        self.assertEqual(self.NAME_TO_RENAME, metadata["name"])
        sa.delete_project(self.NAME_TO_RENAME)

    def test_rename_project_by_id(self):
        project_id = sa.get_project_metadata(self.PROJECT_NAME)["id"]
        sa.rename_project(project_id, self.NEW_PROJECT_NAME)
        meta = sa.get_project_metadata(self.NEW_PROJECT_NAME)
        self.assertEqual(meta["name"], self.NEW_PROJECT_NAME)
        self.assertEqual(meta["id"], project_id)
