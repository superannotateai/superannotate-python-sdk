from unittest import TestCase

from lib.core.exceptions import AppException
from src.superannotate import SAClient

sa = SAClient()


class TestProjectUserPermissions(TestCase):
    PROJECT_NAME = "TestProjectUserPermissions"
    PROJECT_TYPE = "Vector"
    PROJECT_DESCRIPTION = "DESCRIPTION"
    PERMISSION = "Download"

    @classmethod
    def setUpClass(cls, *args, **kwargs) -> None:
        cls.tearDownClass()
        cls._project = sa.create_project(
            cls.PROJECT_NAME, cls.PROJECT_DESCRIPTION, cls.PROJECT_TYPE
        )
        users = sa.list_users()
        scapegoat = [
            u for u in users if u["role"] == "Contributor" and u["state"] == "Confirmed"
        ][0]
        cls.scapegoat = scapegoat
        sa.add_contributors_to_project(
            cls.PROJECT_NAME, [scapegoat["email"]], "ProjectAdmin"
        )

    @classmethod
    def tearDownClass(cls) -> None:
        projects = sa.list_projects(name__in=[cls.PROJECT_NAME])
        for project in projects:
            try:
                sa.delete_project(project=project["id"])
            except Exception as _:
                pass

    def tearDown(self):
        try:
            sa.revoke_project_user_permissions(
                project=self.PROJECT_NAME,
                permissions="*",
                user=self.scapegoat["email"],
            )
        except Exception:
            pass

    def test_grant_permission_by_email(self):
        with self.assertLogs("sa", level="INFO") as cm:
            sa.grant_project_user_permissions(
                project=self.PROJECT_NAME,
                permissions=[self.PERMISSION],
                user=self.scapegoat["email"],
            )
            assert (
                f"INFO:sa:Successfully granted [{self.PERMISSION}] permission(s) "
                f"for user: {self.scapegoat['email']}." == cm.output[0]
            )

    def test_grant_permission_by_project_id_and_user_id(self):
        project = sa.get_project_metadata(self.PROJECT_NAME)
        project_user_id = sa.list_users(
            project=self.PROJECT_NAME, email=self.scapegoat["email"]
        )[0]["id"]

        with self.assertLogs("sa", level="INFO") as cm:
            sa.grant_project_user_permissions(
                project=project["id"],
                permissions=[self.PERMISSION],
                user=project_user_id,
            )
            assert (
                f"INFO:sa:Successfully granted [{self.PERMISSION}] permission(s) "
                f"for user: {self.scapegoat['email']}." == cm.output[0]
            )

    def test_grant_all_permissions_wildcard(self):
        with self.assertLogs("sa", level="INFO") as cm:
            sa.grant_project_user_permissions(
                project=self.PROJECT_NAME,
                permissions="*",
                user=self.scapegoat["email"],
            )
            assert cm.output[0].startswith("INFO:sa:Successfully granted [")
            assert cm.output[0].endswith(
                f"] permission(s) for user: {self.scapegoat['email']}."
            )

    def test_grant_already_granted_logs_failure(self):
        sa.grant_project_user_permissions(
            project=self.PROJECT_NAME,
            permissions=[self.PERMISSION],
            user=self.scapegoat["email"],
        )
        with self.assertLogs("sa", level="INFO") as cm:
            sa.grant_project_user_permissions(
                project=self.PROJECT_NAME,
                permissions=[self.PERMISSION],
                user=self.scapegoat["email"],
            )
            joined = "\n".join(cm.output)
            assert (
                f"Could not grant [{self.PERMISSION}] permission(s) "
                f"for user: {self.scapegoat['email']}." in joined
            )
            assert "Possible reasons:" in joined
            assert (
                f"User already has [{self.PERMISSION}] permission(s) granted." in joined
            )

    def test_revoke_permission(self):
        sa.grant_project_user_permissions(
            project=self.PROJECT_NAME,
            permissions=[self.PERMISSION],
            user=self.scapegoat["email"],
        )
        with self.assertLogs("sa", level="INFO") as cm:
            sa.revoke_project_user_permissions(
                project=self.PROJECT_NAME,
                permissions=[self.PERMISSION],
                user=self.scapegoat["email"],
            )
            assert (
                f"INFO:sa:Successfully revoked [{self.PERMISSION}] permission(s) "
                f"for user: {self.scapegoat['email']}." == cm.output[0]
            )

    def test_revoke_already_revoked_logs_failure(self):
        with self.assertLogs("sa", level="INFO") as cm:
            sa.revoke_project_user_permissions(
                project=self.PROJECT_NAME,
                permissions=[self.PERMISSION],
                user=self.scapegoat["email"],
            )
            joined = "\n".join(cm.output)
            assert (
                f"Could not revoke [{self.PERMISSION}] permission(s) "
                f"for user: {self.scapegoat['email']}." in joined
            )
            assert (
                f"[{self.PERMISSION}] permission(s) were already revoked for the user."
                in joined
            )

    def test_grant_invalid_permission_logs_failure(self):
        with self.assertLogs("sa", level="INFO") as cm:
            sa.grant_project_user_permissions(
                project=self.PROJECT_NAME,
                permissions=["NonExistentPermission"],
                user=self.scapegoat["email"],
            )
            joined = "\n".join(cm.output)
            assert (
                f"Could not grant [NonExistentPermission] permission(s) "
                f"for user: {self.scapegoat['email']}." in joined
            )
            assert "Provided permission(s) were invalid." in joined

    def test_grant_mixed_valid_and_invalid_logs_both(self):
        with self.assertLogs("sa", level="INFO") as cm:
            sa.grant_project_user_permissions(
                project=self.PROJECT_NAME,
                permissions=[self.PERMISSION, "NonExistentPermission"],
                user=self.scapegoat["email"],
            )
            joined = "\n".join(cm.output)
            assert (
                f"Successfully granted [{self.PERMISSION}] permission(s) "
                f"for user: {self.scapegoat['email']}." in joined
            )
            assert (
                f"Could not grant [NonExistentPermission] permission(s) "
                f"for user: {self.scapegoat['email']}." in joined
            )
            assert "Provided permission(s) were invalid." in joined

    def test_grant_mixed_new_and_already_granted_logs_both(self):
        sa.grant_project_user_permissions(
            project=self.PROJECT_NAME,
            permissions=[self.PERMISSION],
            user=self.scapegoat["email"],
        )
        permission_groups = (
            sa.controller.service_provider.work_management.list_permission_groups().data
            or []
        )
        other = next(
            (p.name for p in permission_groups if p.name and p.name != self.PERMISSION),
            None,
        )
        if not other:
            self.skipTest("Need at least 2 permission groups for mixed scenario.")
        with self.assertLogs("sa", level="INFO") as cm:
            sa.grant_project_user_permissions(
                project=self.PROJECT_NAME,
                permissions=[self.PERMISSION, other],
                user=self.scapegoat["email"],
            )
            joined = "\n".join(cm.output)
            assert (
                f"Could not grant [{self.PERMISSION}, {other}] permission(s) "
                f"for user: {self.scapegoat['email']}." in joined
            )
            assert (
                f"User already has [{self.PERMISSION}, {other}] permission(s) granted."
                in joined
            )

    def test_grant_empty_permissions_raises(self):
        with self.assertRaisesRegex(AppException, r"Permission\(s\) cannot be empty\."):
            sa.grant_project_user_permissions(
                project=self.PROJECT_NAME,
                permissions=[],
                user=self.scapegoat["email"],
            )

    def test_revoke_empty_permissions_raises(self):
        with self.assertRaisesRegex(AppException, r"Permission\(s\) cannot be empty\."):
            sa.revoke_project_user_permissions(
                project=self.PROJECT_NAME,
                permissions=[],
                user=self.scapegoat["email"],
            )

    def test_grant_unknown_user_raises(self):
        with self.assertRaisesRegex(AppException, "User not found."):
            sa.grant_project_user_permissions(
                project=self.PROJECT_NAME,
                permissions=[self.PERMISSION],
                user="non_existent_user@superannotate.com",
            )
