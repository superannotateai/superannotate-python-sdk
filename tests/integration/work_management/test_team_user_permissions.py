from unittest import TestCase

from lib.core.exceptions import AppException
from src.superannotate import SAClient

sa = SAClient()


class TestTeamUserPermissions(TestCase):
    # Apostrophe-free contributor permission so exact log assertions are stable
    # regardless of the backend's curly/straight apostrophe rendering.
    PERMISSION = "Invite Contributors to team"
    # Contributor permission whose canonical name uses a curly apostrophe.
    CURLY_PERMISSION = "View Contributors’ scores"

    @classmethod
    def setUpClass(cls, *args, **kwargs) -> None:
        users = sa.list_users()
        contributors = [
            u
            for u in users
            if u["role"] == "Contributor" and u["state"] == "Confirmed"
        ]
        if not contributors:
            raise RuntimeError(
                "No confirmed contributor available for team-user permission tests."
            )
        cls.scapegoat = contributors[0]
        # Reset to the zero-permission baseline; each test then grants only the
        # permissions it needs.
        cls._reset(cls.scapegoat["email"])

    @classmethod
    def tearDownClass(cls) -> None:
        cls._reset(cls.scapegoat["email"])

    @classmethod
    def _reset(cls, email):
        # Reset a team user to the zero-permission baseline. A plain revoke
        # cannot remove "Manage Contributors' permissions" (the backend blocks
        # revoking contributor permissions while the master is enabled), so use
        # the full "setpermissions" replace with an empty set, which clears
        # every permission including the master.
        contributor_id = sa.list_users(email=email)[0]["id"]
        sa.controller.service_provider.work_management.set_team_user_permissions(
            contributor_ids=[contributor_id],
            permission_ids=[],
        )

    def tearDown(self):
        self._reset(self.scapegoat["email"])

    @staticmethod
    def _has_master(perms):
        return any("Manage Contributors" in (p.get("name") or "") for p in perms)

    def test_grant_permission_by_email(self):
        with self.assertLogs("sa", level="INFO") as cm:
            sa.grant_team_user_permissions(
                permissions=[self.PERMISSION],
                user=self.scapegoat["email"],
            )
            assert (
                f"INFO:sa:Successfully granted [{self.PERMISSION}] permission(s) "
                f"for user: {self.scapegoat['email']}." == cm.output[0]
            )

    def test_grant_permission_by_user_id(self):
        team_user_id = sa.list_users(email=self.scapegoat["email"])[0]["id"]
        with self.assertLogs("sa", level="INFO") as cm:
            sa.grant_team_user_permissions(
                permissions=[self.PERMISSION],
                user=team_user_id,
            )
            assert (
                f"INFO:sa:Successfully granted [{self.PERMISSION}] permission(s) "
                f"for user: {self.scapegoat['email']}." == cm.output[0]
            )

    def test_grant_all_permissions_wildcard(self):
        # "*" grants every permission available for the contributor role,
        # including the "Manage Contributors' permissions" master. The
        # scapegoat starts clean (setUpClass / tearDown) so no separate user
        # is needed; tearDown resets it to the zero-permission baseline.
        email = self.scapegoat["email"]
        with self.assertLogs("sa", level="INFO") as cm:
            sa.grant_team_user_permissions(permissions="*", user=email)
        success = [o for o in cm.output if o.startswith("INFO:sa:Successfully granted [")]
        self.assertTrue(success, f"expected success log, got {cm.output}")
        line = success[0]
        for key in (
            "Manage Contributors",
            "Invite Contributors to team",
            "Remove Contributors from team",
            "Access Workload management",
        ):
            self.assertIn(key, line)
        granted = {
            p["name"]
            for p in (sa.list_users(email=email)[0].get("user_permissions") or [])
        }
        self.assertEqual(len(granted), 7)
        self.assertTrue(self._has_master([{"name": n} for n in granted]))

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
            assert (
                f"Could not grant [{self.PERMISSION}] permission(s) "
                f"for user: {self.scapegoat['email']}." in joined
            )
            assert "Possible reasons:" in joined
            assert (
                f"User already has [{self.PERMISSION}] permission(s) granted."
                in joined
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
            assert (
                f"INFO:sa:Successfully revoked [{self.PERMISSION}] permission(s) "
                f"for user: {self.scapegoat['email']}." == cm.output[0]
            )

    def test_revoke_already_revoked_logs_failure(self):
        with self.assertLogs("sa", level="INFO") as cm:
            sa.revoke_team_user_permissions(
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
            sa.grant_team_user_permissions(
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
            sa.grant_team_user_permissions(
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

    def test_grant_apostrophe_normalization(self):
        # The backend stores the canonical name with a curly apostrophe, but
        # users should be able to grant using a straight apostrophe too.
        with self.assertLogs("sa", level="INFO") as cm:
            sa.grant_team_user_permissions(
                permissions=["View Contributors' scores"],
                user=self.scapegoat["email"],
            )
            joined = "\n".join(cm.output)
            assert (
                f"Successfully granted [{self.CURLY_PERMISSION}] permission(s) "
                f"for user: {self.scapegoat['email']}." in joined
            )

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
                user="non_existent_user@superannotate.com",
            )

    def test_revoke_unknown_user_raises(self):
        with self.assertRaisesRegex(AppException, "User not found."):
            sa.revoke_team_user_permissions(
                permissions=[self.PERMISSION],
                user="non_existent_user@superannotate.com",
            )

    def test_grant_manage_contributors_permissions_cascade(self):
        # Granting "Manage Contributors' permissions" must cascade to all
        # contributor permissions. The scapegoat starts clean and tearDown
        # resets it to the zero-permission baseline, so no separate user is
        # needed.
        email = self.scapegoat["email"]
        with self.assertLogs("sa", level="INFO") as cm:
            sa.grant_team_user_permissions(
                permissions=["Manage Contributors' permissions"],
                user=email,
            )
        success = [o for o in cm.output if o.startswith("INFO:sa:Successfully granted [")]
        self.assertTrue(success, f"expected success log, got {cm.output}")
        line = success[0]
        for key in (
            "Manage Contributors",
            "Invite Contributors to team",
            "Remove Contributors from team",
            "View Contributors",
            "Edit Contributors",
            "Access Workload management",
        ):
            self.assertIn(key, line)
        granted = {
            p["name"]
            for p in (sa.list_users(email=email)[0].get("user_permissions") or [])
        }
        self.assertEqual(len(granted), 7)

    def test_revoke_blocked_while_manage_enabled(self):
        # While "Manage Contributors' permissions" is enabled, other
        # contributor permissions cannot be revoked. Establish that
        # precondition on the clean scapegoat by granting the master (which
        # cascades to every contributor permission); tearDown resets it to the
        # zero-permission baseline.
        email = self.scapegoat["email"]
        sa.grant_team_user_permissions(
            permissions=["Manage Contributors' permissions"],
            user=email,
        )
        self.assertTrue(
            self._has_master(
                sa.list_users(email=email)[0].get("user_permissions") or []
            ),
            "setup failed: master permission was not granted",
        )
        with self.assertLogs("sa", level="INFO") as cm:
            sa.revoke_team_user_permissions(
                permissions=["Remove Contributors from team"],
                user=email,
            )
        failure = [o for o in cm.output if o.startswith("INFO:sa:Could not revoke [")]
        self.assertTrue(failure, f"expected failure log, got {cm.output}")
        joined = "\n".join(failure)
        self.assertIn("Remove Contributors from team", joined)
        self.assertIn(
            "If Manage Contributors' permissions is granted, it must be "
            "revoked before",
            joined,
        )

    def test_revoke_view_custom_field_values_cascade(self):
        # Revoking "View Contributors' custom field values" must also revoke
        # "Edit Contributors' custom field values". Granting "Edit" first
        # also exercises the grant cascade (Edit auto-grants View). Both
        # cascades are reversible (no master permission involved), so this
        # runs on the clean scapegoat.
        with self.assertLogs("sa", level="INFO") as cm:
            sa.grant_team_user_permissions(
                permissions=["Edit Contributors' custom field values"],
                user=self.scapegoat["email"],
            )
        granted = {
            p["name"]
            for p in (sa.list_users(email=self.scapegoat["email"])[0].get("user_permissions") or [])
        }
        self.assertTrue(
            any("View Contributors" in n and "custom field values" in n for n in granted),
            f"grant cascade should have granted View, got {granted}",
        )
        self.assertTrue(
            any("Edit Contributors" in n for n in granted),
            f"grant should have granted Edit, got {granted}",
        )
        with self.assertLogs("sa", level="INFO") as cm:
            sa.revoke_team_user_permissions(
                permissions=["View Contributors' custom field values"],
                user=self.scapegoat["email"],
            )
        success = [o for o in cm.output if o.startswith("INFO:sa:Successfully revoked [")]
        self.assertTrue(success, f"expected success log, got {cm.output}")
        joined = "\n".join(success)
        self.assertIn("View Contributors", joined)
        self.assertIn("Edit Contributors", joined)
        remaining = {
            p["name"]
            for p in (sa.list_users(email=self.scapegoat["email"])[0].get("user_permissions") or [])
        }
        self.assertFalse(
            any("custom field values" in n for n in remaining),
            f"expected both custom-field-value permissions revoked, got {remaining}",
        )
