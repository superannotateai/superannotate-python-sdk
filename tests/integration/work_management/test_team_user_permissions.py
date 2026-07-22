from unittest import TestCase

from lib.core import TEAM_USER_PERMISSION_MANAGE_CONTRIBUTORS
from lib.core.exceptions import AppException
from src.superannotate import SAClient

sa = SAClient()


class TestTeamUserPermissions(TestCase):
    # Apostrophe-free contributor permission so exact log assertions are stable
    # regardless of the backend's curly/straight apostrophe rendering.
    PERMISSION = "Invite Contributors to team"
    # Contributor permission whose canonical name uses a curly apostrophe.
    CURLY_PERMISSION = "View Contributors’ scores"
    # An admin-only permission; granting it to a contributor must be rejected.
    ADMIN_PERMISSION = "View SDK Token"

    @classmethod
    def setUpClass(cls, *args, **kwargs) -> None:
        # Scapegoat for the per-permission tests: a contributor without the
        # "Manage Contributors' permissions" master, kept clean by _reset().
        cls.scapegoat = cls._find_contributor_without_master()
        if cls.scapegoat is None:
            raise RuntimeError(
                "No contributor without 'Manage Contributors' permissions "
                "available for team-user permission tests."
            )
        cls._reset(cls.scapegoat["email"])

    @classmethod
    def tearDownClass(cls) -> None:
        cls._reset(cls.scapegoat["email"])

    @classmethod
    def _reset(cls, email):
        # Reset a team user by revoking every permission individually via the
        # grant/revoke delta endpoint. "Manage Contributors' permissions"
        # (id 19) cannot be revoked this way (the backend blocks revoking
        # contributor permissions while the master is enabled), so it is
        # skipped; the per-permission tests never grant it, and the
        # master-granting tests run on a separate, disposable contributor.
        contributor_id = sa.list_users(email=email)[0]["id"]
        name_by_id = sa.controller.service_provider.get_team_user_permission_id_name_map()
        master_id = TEAM_USER_PERMISSION_MANAGE_CONTRIBUTORS["id"]
        for pid in name_by_id:
            if pid == master_id:
                continue
            try:
                sa.controller.service_provider.work_management.edit_team_user_permissions(
                    contributor_ids=[contributor_id],
                    permission_ids=[pid],
                    operation="revoke",
                )
            except Exception:
                pass

    def tearDown(self):
        self._reset(self.scapegoat["email"])

    @staticmethod
    def _has_master(perms):
        return any("Manage Contributors" in (p.get("name") or "") for p in perms)

    @classmethod
    def _find_contributor_without_master(cls, exclude_email=None):
        for u in sa.list_users():
            if u.get("role") != "Contributor" or u.get("state") != "Confirmed":
                continue
            if u.get("email") == exclude_email:
                continue
            full = sa.list_users(email=u["email"])[0]
            if not cls._has_master(full.get("user_permissions") or []):
                return u
        return None

    @classmethod
    def _find_contributor_with_master(cls):
        for u in sa.list_users():
            if u.get("role") != "Contributor" or u.get("state") != "Confirmed":
                continue
            full = sa.list_users(email=u["email"])[0]
            if cls._has_master(full.get("user_permissions") or []):
                return u
        return None

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
        # including the "Manage Contributors' permissions" master, which is
        # irreversible via the permissions API. Run it on a disposable
        # contributor that does not yet have the master (never the main
        # scapegoat); skip if none is available.
        target = self._find_contributor_without_master(
            exclude_email=self.scapegoat["email"]
        )
        if target is None:
            self.skipTest(
                "No contributor without 'Manage Contributors' permissions "
                "available; wildcard grant is irreversible."
            )
        email = target["email"]
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

    def test_grant_admin_permission_for_contributor_logs_failure(self):
        # Admin-only permissions must not be grantable to a contributor; the
        # backend rejects the batch and the SDK reports a role-mismatch failure
        # with the full "Possible reasons" block.
        with self.assertLogs("sa", level="INFO") as cm:
            sa.grant_team_user_permissions(
                permissions=[self.ADMIN_PERMISSION],
                user=self.scapegoat["email"],
            )
            joined = "\n".join(cm.output)
            self.assertIn(
                f"Could not grant [{self.ADMIN_PERMISSION}] permission(s) "
                f"for user: {self.scapegoat['email']}.",
                joined,
            )
            self.assertIn(
                f"User role does not allow [{self.ADMIN_PERMISSION}] "
                f"permission(s).",
                joined,
            )
        # Sanity: the admin permission was not actually granted.
        granted = {
            p["name"]
            for p in (
                sa.list_users(email=self.scapegoat["email"])[0].get(
                    "user_permissions"
                )
                or []
            )
        }
        self.assertNotIn(self.ADMIN_PERMISSION, granted)

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
        # contributor permissions. The master is irreversible, so run on a
        # disposable contributor that does not yet have it.
        target = self._find_contributor_without_master(
            exclude_email=self.scapegoat["email"]
        )
        if target is None:
            self.skipTest(
                "No contributor without 'Manage Contributors' permissions "
                "available; cascade grant is irreversible."
            )
        email = target["email"]
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
        # contributor permissions cannot be revoked. Prefer reusing a
        # contributor that already has the master (irreversible, so it stays
        # enabled between runs); otherwise grant it on a disposable one.
        target = self._find_contributor_with_master()
        if target is None:
            target = self._find_contributor_without_master(
                exclude_email=self.scapegoat["email"]
            )
        if target is None:
            self.skipTest(
                "No contributor available to verify the revoke block."
            )
        email = target["email"]
        if not self._has_master(
            sa.list_users(email=email)[0].get("user_permissions") or []
        ):
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
