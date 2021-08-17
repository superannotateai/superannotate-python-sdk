import src.lib.app.superannotate as sa
from src.tests.integration.base import BaseTestCase


class TestUserRoles(BaseTestCase):
    PROJECT_NAME = "test users and roles"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"

    def test_users_roles(self):

        user = sa.search_team_contributors()[0]
        sa.share_project(self.PROJECT_NAME, user, "QA")
        project_users = sa.get_project_metadata(
            self.PROJECT_NAME, include_contributors=True
        )["contributors"]
        found = False
        for u in project_users:
            if u["user_id"] == user["id"]:
                found = True
                break
        self.assertTrue(found and user)

        sa.unshare_project(self.PROJECT_NAME, user)
        project_users = sa.get_project_metadata(
            self.PROJECT_NAME, include_contributors=True
        )["contributors"]
        found = False
        for u in project_users:
            if u["user_id"] == user["id"]:
                found = True
                break
        self.assertFalse(found and user)
