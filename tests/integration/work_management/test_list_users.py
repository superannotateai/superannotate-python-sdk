import contextlib

import pytest
from superannotate import SAClient
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestListUsers(BaseTestCase):
    PROJECT_NAME = "TestListUsers"
    PROJECT_NAME_2 = "TestListUsersProjectPermissions"
    PROJECT_TYPE = "Vector"

    def setUp(self):
        super().setUp()
        sa.create_project(self.PROJECT_NAME_2, "desc", self.PROJECT_TYPE)
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

    def tearDown(self) -> None:
        super().tearDown()
        with contextlib.suppress(Exception):
            sa.delete_project(self.PROJECT_NAME_2)

    @pytest.mark.skip(reason="For not send real email")
    def test_pending_users(self):
        test_email = "test1@superannotate.com"
        sa.invite_contributors_to_team(emails=[test_email])
        sa.add_contributors_to_project(self.PROJECT_NAME, [test_email], "Annotator")
        sa.clone_project("narek test5", self.PROJECT_NAME, copy_contributors=True)
        project = sa.get_project_metadata("narek test5", include_contributors=True)

        assert project["contributors"][1]["state"] == "PENDING"

    @pytest.mark.skip(reason="For not send real email")
    def test_project_role_filter_users(self):
        test_email = "test1@superannotate.com"
        sa.invite_contributors_to_team(emails=[test_email])
        sa.add_contributors_to_project(self.PROJECT_NAME, [test_email], "Annotator")
        users = sa.list_users(project=self.PROJECT_NAME, role="QA")
        assert len(users) == 0
        users = sa.list_users(project=self.PROJECT_NAME, role="Annotator")
        assert len(users) == 2

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

    def test_list_users_include_project_permissions(self):
        project_users = sa.list_users(
            project=self.PROJECT_NAME,
            email=self.scapegoat["email"],
            include=["project_permissions"],
        )
        assert len(project_users) == 1
        user = project_users[0]
        assert "project_permissions" in user
        assert isinstance(user["project_permissions"], list)

    def test_list_users_include_project_permissions_after_grant(self):
        permission = "Download"
        sa.add_contributors_to_project(
            self.PROJECT_NAME_2, [self.scapegoat["email"]], "ProjectAdmin"
        )
        sa.grant_project_user_permissions(
            project=self.PROJECT_NAME_2,
            permissions=[permission],
            user=self.scapegoat["email"],
        )
        project_users = sa.list_users(
            project=self.PROJECT_NAME_2,
            email=self.scapegoat["email"],
            include=["project_permissions"],
        )
        assert len(project_users) == 1
        user = project_users[0]
        assert isinstance(user.get("project_permissions"), list)
        granted_names = {p.get("name") for p in user["project_permissions"]}
        assert permission in granted_names
