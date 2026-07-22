from unittest import TestCase

from lib.core.exceptions import AppException
from src.superannotate import SAClient

sa = SAClient()


class TestTeamAdminUserPermissions(TestCase):
    # Team-admin permissions (ids 26, 27) have no apostrophes, so exact log
    # assertions are stable. They are reversible via the permissions API (no
    # irrevocable master like the contributor "Manage Contributors' permissions").
    PERMISSION = "View SDK Token"
    OTHER_PERMISSION = "Access Orchestrate"
    # A contributor-only permission; granting it to an admin must be rejected.
    CONTRIBUTOR_PERMISSION = "Invite Contributors to team"

    @classmethod
    def setUpClass(cls, *args, **kwargs) -> None:
        cls.scapegoat = cls._find_admin(clean=True)
        cls._cleanup()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._cleanup()

    @classmethod
    def _find_admin(cls, clean: bool = False):
        users = sa.list_users()
        admins = [
            u
            for u in users
            if u.get("state") == "Confirmed" and u.get("role") in ("TeamAdmin", "TeamOwner")
        ]
        if not clean:
            return admins[0]
        for u in admins:
            full = sa.list_users(email=u["email"])[0]
            if not (full.get("user_permissions") or []):
                return u
        return admins[0]

    @classmethod
    def _cleanup(cls):
        # Admin permissions are reversible, so revoking each one individually
        # reliably restores a clean state.
        for name in (cls.OTHER_PERMISSION, cls.PERMISSION):
            try:
                sa.revoke_team_user_permissions(
                    permissions=[name],
                    user=cls.scapegoat["email"],
                )
            except Exception:
                pass

    def tearDown(self):
        self._cleanup()

    def test_grant_permission_by_email(self):
        with self.assertLogs("sa", level="INFO") as cm:
            sa.grant_team_user_permissions(
                permissions=[self.PERMISSION],
                user=self.scapegoat["email"],
            )
            self.assertEqual(
                cm.output[0],
                f"INFO:sa:Successfully granted [{self.PERMISSION}] permission(s) "
                f"for user: {self.scapegoat['email']}.",
            )

    def test_grant_permission_by_user_id(self):
        team_user_id = sa.list_users(email=self.scapegoat["email"])[0]["id"]
        with self.assertLogs("sa", level="INFO") as cm:
            sa.grant_team_user_permissions(
                permissions=[self.OTHER_PERMISSION],
                user=team_user_id,
            )
            self.assertEqual(
                cm.output[0],
                f"INFO:sa:Successfully granted [{self.OTHER_PERMISSION}] "
                f"permission(s) for user: {self.scapegoat['email']}.",
            )

    def test_grant_all_permissions_wildcard(self):
        # "*" resolves to the admin role's permissions (View SDK Token +
        # Access Orchestrate). Unlike the contributor wildcard, this is fully
        # reversible, so it can be exercised idempotently.
        with self.assertLogs("sa", level="INFO") as cm:
            sa.grant_team_user_permissions(
                permissions="*",
                user=self.scapegoat["email"],
            )
            joined = "\n".join(cm.output)
            self.assertIn(
                f"Successfully granted [{self.PERMISSION}, {self.OTHER_PERMISSION}] "
                f"permission(s) for user: {self.scapegoat['email']}.",
                joined,
            )
        granted = {
            p["name"]
            for p in (
                sa.list_users(email=self.scapegoat["email"])[0].get(
                    "user_permissions"
                )
                or []
            )
        }
        self.assertEqual(granted, {self.PERMISSION, self.OTHER_PERMISSION})

    def test_grant_already_granted_logs_failure(self):
        sa.grant_team_user_permissions(
            permissions=[self.PERMISSION],
            user=self.scapegoat["email"],
        )
        with self.assertLogs("sa", level="INFO") as cm:
            sa.grant_team_user_permissions(
                permissions=[self.PERMISSION],
                user=self.scapegoat["email"],
            )
            joined = "\n".join(cm.output)
            self.assertIn(
                f"Could not grant [{self.PERMISSION}] permission(s) "
                f"for user: {self.scapegoat['email']}.",
                joined,
            )
            self.assertIn(
                f"User already has [{self.PERMISSION}] permission(s) granted.",
                joined,
            )

    def test_revoke_permission(self):
        sa.grant_team_user_permissions(
            permissions=[self.PERMISSION],
            user=self.scapegoat["email"],
        )
        with self.assertLogs("sa", level="INFO") as cm:
            sa.revoke_team_user_permissions(
                permissions=[self.PERMISSION],
                user=self.scapegoat["email"],
            )
            self.assertEqual(
                cm.output[0],
                f"INFO:sa:Successfully revoked [{self.PERMISSION}] permission(s) "
                f"for user: {self.scapegoat['email']}.",
            )

    def test_revoke_already_revoked_logs_failure(self):
        with self.assertLogs("sa", level="INFO") as cm:
            sa.revoke_team_user_permissions(
                permissions=[self.PERMISSION],
                user=self.scapegoat["email"],
            )
            joined = "\n".join(cm.output)
            self.assertIn(
                f"Could not revoke [{self.PERMISSION}] permission(s) "
                f"for user: {self.scapegoat['email']}.",
                joined,
            )
            self.assertIn(
                f"[{self.PERMISSION}] permission(s) were already revoked for the user.",
                joined,
            )

    def test_grant_invalid_permission_logs_failure(self):
        with self.assertLogs("sa", level="INFO") as cm:
            sa.grant_team_user_permissions(
                permissions=["NonExistentPermission"],
                user=self.scapegoat["email"],
            )
            joined = "\n".join(cm.output)
            self.assertIn(
                f"Could not grant [NonExistentPermission] permission(s) "
                f"for user: {self.scapegoat['email']}.",
                joined,
            )
            self.assertIn("Provided permission(s) were invalid.", joined)

    def test_grant_mixed_valid_and_invalid_logs_both(self):
        with self.assertLogs("sa", level="INFO") as cm:
            sa.grant_team_user_permissions(
                permissions=[self.PERMISSION, "NonExistentPermission"],
                user=self.scapegoat["email"],
            )
            joined = "\n".join(cm.output)
            self.assertIn(
                f"Successfully granted [{self.PERMISSION}] permission(s) "
                f"for user: {self.scapegoat['email']}.",
                joined,
            )
            self.assertIn(
                f"Could not grant [NonExistentPermission] permission(s) "
                f"for user: {self.scapegoat['email']}.",
                joined,
            )
            self.assertIn("Provided permission(s) were invalid.", joined)

    def test_grant_contributor_permission_for_admin_logs_failure(self):
        # Contributor-only permissions must not be grantable to an admin; the
        # backend rejects the batch and the SDK reports a role-mismatch failure.
        with self.assertLogs("sa", level="INFO") as cm:
            sa.grant_team_user_permissions(
                permissions=[self.CONTRIBUTOR_PERMISSION],
                user=self.scapegoat["email"],
            )
            joined = "\n".join(cm.output)
            self.assertIn(
                f"Could not grant [{self.CONTRIBUTOR_PERMISSION}] permission(s) "
                f"for user: {self.scapegoat['email']}.",
                joined,
            )
            self.assertIn(
                f"User role does not allow [{self.CONTRIBUTOR_PERMISSION}] "
                f"permission(s).",
                joined,
            )
        # Sanity: the contributor permission was not actually granted.
        granted = {
            p["name"]
            for p in (
                sa.list_users(email=self.scapegoat["email"])[0].get(
                    "user_permissions"
                )
                or []
            )
        }
        self.assertNotIn(self.CONTRIBUTOR_PERMISSION, granted)

    def test_grant_empty_permissions_raises(self):
        with self.assertRaisesRegex(AppException, r"Permission\(s\) cannot be empty\."):
            sa.grant_team_user_permissions(
                permissions=[],
                user=self.scapegoat["email"],
            )

    def test_revoke_empty_permissions_raises(self):
        with self.assertRaisesRegex(AppException, r"Permission\(s\) cannot be empty\."):
            sa.revoke_team_user_permissions(
                permissions=[],
                user=self.scapegoat["email"],
            )

    def test_grant_unknown_user_raises(self):
        with self.assertRaisesRegex(AppException, "User not found."):
            sa.grant_team_user_permissions(
                permissions=[self.PERMISSION],
                user="non_existent_admin@superannotate.com",
            )

    def test_revoke_unknown_user_raises(self):
        with self.assertRaisesRegex(AppException, "User not found."):
            sa.revoke_team_user_permissions(
                permissions=[self.PERMISSION],
                user="non_existent_admin@superannotate.com",
            )
