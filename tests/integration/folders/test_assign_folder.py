from superannotate import SAClient
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestAssignFolderToUsers(BaseTestCase):
    PROJECT_NAME = "TestAssignFolderToUsers"
    PROJECT_TYPE = "Vector"
    FOLDER_NAME = "test_folder_assign"

    def setUp(self):
        super().setUp()
        team_users = sa.list_users()
        assert len(team_users) > 0
        self.scapegoat_accepted = next(
            (
                u
                for u in team_users
                if u["state"] == "Confirmed" and u["role"] == "Contributor"
            ),
            None,
        )
        self.scapegoat_pending = next(
            (
                u
                for u in team_users
                if u["state"] == "Pending" and u["role"] == "Contributor"
            ),
            None,
        )
        sa.add_contributors_to_project(
            self.PROJECT_NAME,
            [self.scapegoat_accepted["email"], self.scapegoat_pending["email"]],
            "Annotator",
        )
        project_users = sa.list_users(project=self.PROJECT_NAME)
        assert len(project_users) == 2

    def test_assign_folder_to_users(self):
        # create folder
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_NAME)

        sa.assign_folder(
            self.PROJECT_NAME,
            self.FOLDER_NAME,
            [self.scapegoat_accepted["email"], self.scapegoat_pending["email"]],
        )
