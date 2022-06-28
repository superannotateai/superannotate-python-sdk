from src.superannotate import SAClient

from tests.integration.base import BaseTestCase

sa = SAClient()


class TestTeam(BaseTestCase):
    PROJECT_NAME = "test_team"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PTH = "data_set"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"

    def test_team_metadata(self):
        metadata = sa.get_team_metadata()
        self.assertTrue(
            all([x in metadata for x in ["id", "users", "name", "description", "type"]])
        )

        for user in metadata["users"]:
            self.assertTrue(
                all(
                    [
                        x in user
                        for x in ["id", "email", "first_name", "last_name", "user_role"]
                    ]
                )
            )
