import os
from os.path import dirname
from unittest import TestCase

import src.superannotate as sa


class TestCloneProject(TestCase):
    PROJECT_NAME_1 = "test create from full info1"
    PROJECT_NAME_2 = "test create from full info2"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"

    TEST_FOLDER_PATH = "data_set/sample_project_vector"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    @property
    def classes_json(self):
        return f"{self.folder_path}/classes/classes.json"

    def setUp(self, *args, **kwargs):
        self.tearDown()
        self._project_1 = sa.create_project(
            self.PROJECT_NAME_1, self.PROJECT_DESCRIPTION, self.PROJECT_TYPE
        )

    def tearDown(self) -> None:
        sa.delete_project(self.PROJECT_NAME_1)
        sa.delete_project(self.PROJECT_NAME_2)

    def test_clone_contributors_and_description(self):
        team_users = sa.search_team_contributors()
        sa.share_project(self.PROJECT_NAME_1, team_users[0], "QA")
        first_project_metadata = sa.get_project_metadata(
            self.PROJECT_NAME_1, include_contributors=True
        )
        first_project_contributors = first_project_metadata["contributors"]
        sa.clone_project(self.PROJECT_NAME_2, self.PROJECT_NAME_1, "DESCRIPTION", copy_contributors=True)
        second_project_metadata = sa.get_project_metadata(
            self.PROJECT_NAME_2, include_contributors=True
        )
        second_project_contributors = second_project_metadata["contributors"]

        self.assertEqual(first_project_contributors[0]["user_id"], second_project_contributors[0]["user_id"])
        self.assertEqual("DESCRIPTION", second_project_metadata["description"])