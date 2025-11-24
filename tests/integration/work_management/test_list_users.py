import pytest
from superannotate import SAClient
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestListUsers(BaseTestCase):
    PROJECT_NAME = "TestListUsers"
    PROJECT_TYPE = "Vector"

    def setUp(self):
        super().setUp()
        team_users = sa.list_users()
        assert len(team_users) > 0
        scapegoat = [
            u
            for u in team_users
            if u["role"] == "Contributor" and u["state"] == "Confirmed"
        ][0]
        self.scapegoat = scapegoat
        sa.add_contributors_to_project(
            self.PROJECT_NAME, [scapegoat["email"]], "Annotator"
        )

    @pytest.mark.skip(reason="For not send real email")
    def test_pending_users(self):
        test_email = "test@superannotate.com"
        sa.invite_contributors_to_team(emails=[test_email])
        sa.add_contributors_to_project(self.PROJECT_NAME, [test_email], "Annotator")
        project = sa.get_project_metadata(self.PROJECT_NAME, include_contributors=True)
        assert project['contributors'][1]["state"] == "Pending"

    def test_list_users_by_project_name(self):
        project_users = sa.list_users(project=self.PROJECT_NAME)
        assert len(project_users) == 1
        user_1 = project_users[0]
        assert user_1["role"] == "Annotator"
        assert user_1["email"] == self.scapegoat["email"]

    def test_list_users_by_project_ID(self):
        project = sa.get_project_metadata(self.PROJECT_NAME)
        project_users = sa.list_users(project=project["id"])
        assert len(project_users) == 1
        user_1 = project_users[0]
        assert user_1["role"] == "Annotator"
        assert user_1["email"] == self.scapegoat["email"]
