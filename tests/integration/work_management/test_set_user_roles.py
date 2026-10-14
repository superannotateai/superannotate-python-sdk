from unittest import TestCase

from src.superannotate import AppException
from src.superannotate import SAClient

sa = SAClient()


class TestSetProjectUserRole(TestCase):
    PROJECT_NAME = "TestSetProjectUserRole"
    PROJECT_TYPE = "Vector"
    PENDING_USER = "satest2277@gmail.com"

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        cls.tearDownClass()
        sa.create_project(cls.PROJECT_NAME, "desc", cls.PROJECT_TYPE)
        users = sa.list_users()
        cls.scapegoat = [
            u for u in users if u["role"] == "Contributor" and u["state"] == "Confirmed"
        ][0]
        sa.add_contributors_to_project(
            cls.PROJECT_NAME, [cls.scapegoat["email"]], "Annotator"
        )

    @classmethod
    def tearDownClass(cls) -> None:
        for project in sa.list_projects(name=cls.PROJECT_NAME):
            sa.delete_project(project["id"])

    def _project_role(self, email):
        return sa.list_users(project=self.PROJECT_NAME, email=email)[0]["role"]

    def test_set_project_user_role(self):
        email = self.scapegoat["email"]
        for role in ("QA", "ProjectAdmin", "Annotator"):
            with self.assertLogs("sa", level="INFO") as cm:
                sa.set_project_user_role(
                    project=self.PROJECT_NAME, user=email, role=role
                )
            self.assertEqual(
                f"INFO:sa:Successfully set role {role} for user: {email} "
                f"in project {self.PROJECT_NAME}.",
                cm.output[0],
            )
            self.assertEqual(self._project_role(email), role)

    def test_set_project_user_role_by_project_id(self):
        email = self.scapegoat["email"]
        project_id = sa.get_project_metadata(self.PROJECT_NAME)["id"]
        sa.set_project_user_role(project=project_id, user=email, role="QA")
        self.assertEqual(self._project_role(email), "QA")
        sa.set_project_user_role(project=project_id, user=email, role="Annotator")

    def test_set_project_user_role_pending_user(self):
        if self.PENDING_USER not in [u["email"] for u in sa.list_users()]:
            sa.invite_contributors_to_team(emails=[self.PENDING_USER])
        sa.add_contributors_to_project(
            self.PROJECT_NAME, [self.PENDING_USER], "Annotator"
        )
        sa.set_project_user_role(
            project=self.PROJECT_NAME, user=self.PENDING_USER, role="QA"
        )
        self.assertEqual(self._project_role(self.PENDING_USER), "QA")

    def test_set_project_user_role_invalid_role(self):
        for role in ("Invalid role", "qa", "projectadmin"):
            with self.assertRaisesRegex(AppException, "Invalid role."):
                sa.set_project_user_role(
                    project=self.PROJECT_NAME,
                    user=self.scapegoat["email"],
                    role=role,
                )

    def test_set_project_user_role_invalid_project(self):
        with self.assertRaisesRegex(AppException, "Project not found."):
            sa.set_project_user_role(
                project="Invalid project name",
                user=self.scapegoat["email"],
                role="QA",
            )

    def test_set_project_user_role_user_not_in_project(self):
        with self.assertRaisesRegex(AppException, "User not found."):
            sa.set_project_user_role(
                project=self.PROJECT_NAME,
                user="non_existent_user@superannotate.com",
                role="QA",
            )


class TestSetTeamUserRole(TestCase):
    INVALID_ROLE_ERROR = "Invalid role. Valid roles are: Contributor, Team Admin"

    def test_set_team_user_role_invalid_role(self):
        user = sa.list_users(role="Contributor")[0]["email"]
        for role in ("Admin", "teamadmin", "Team Admin", "TeamOwner", "contributor"):
            with self.assertRaisesRegex(AppException, self.INVALID_ROLE_ERROR):
                sa.set_team_user_role(user=user, role=role)

    def test_set_team_user_role_user_not_found(self):
        with self.assertRaisesRegex(AppException, "User not found."):
            sa.set_team_user_role(
                user="non_existent_user@superannotate.com", role="TeamAdmin"
            )
