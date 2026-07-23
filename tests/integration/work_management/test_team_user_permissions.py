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
    # An admin-only permission; granting it to a contributor must be rejected.
    ADMIN_PERMISSION = "View SDK Token"
    # Reversible cascade pair (no master involved): granting Edit auto-grants
    # View, revoking View auto-revokes Edit. Straight apostrophes here; the SDK
    # normalizes them to match the backend's canonical (curly) names.
    EDIT_CUSTOM_FIELDS = "Edit Contributors' custom field values"
    VIEW_CUSTOM_FIELDS = "View Contributors' custom field values"

    @classmethod
    def setUpClass(cls, *args, **kwargs) -> None:
        # Scapegoat for the per-permission tests: any contributor without the
        # (irreversible) "Manage Contributors' permissions" master. We don't
        # need a pre-clean user — _reset() normalizes the chosen user to a
        # known baseline by granting/revoking the required permissions, and
        # teardown restores it. Prefer a Confirmed contributor; fall back to
        # any state (e.g. Pending), since individual permissions can still be
        # granted and revoked on them.
        cls.scapegoat = cls._find_contributor_without_master()
        if cls.scapegoat is None:
            cls.scapegoat = cls._find_contributor_without_master(
                require_confirmed=False
            )
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
        # Reset a team user to no permissions via the declarative
        # setpermissions endpoint. Unlike the old delta endpoint this also
        # clears the "Manage Contributors' permissions" master, so the master /
        # wildcard tests are fully reversible and need no disposable user.
        contributor_id = sa.list_users(email=email)[0]["id"]
        sa.controller.service_provider.work_management.set_team_user_permissions(
            contributor_id=contributor_id,
            permission_ids=[],
        )

    def tearDown(self):
        self._reset(self.scapegoat["email"])

    @staticmethod
    def _has_master(perms):
        return any("Manage Contributors" in (p.get("name") or "") for p in perms)

    @staticmethod
    def _contributor_permission_names():
        # The full set of contributor permissions that actually exist for this
        # team (id 25 may be absent depending on configuration), used to assert
        # the master/wildcard cascade without hardcoding the count.
        groups = sa.controller.service_provider.get_team_user_permission_groups()
        for name, perms in groups.items():
            if "contributor" in name.lower():
                return set(perms.values())
        return set()

    @classmethod
    def _find_contributor_without_master(
        cls, exclude_email=None, require_confirmed=True
    ):
        for u in sa.list_users():
            if u.get("role") != "Contributor":
                continue
            if require_confirmed and u.get("state") != "Confirmed":
                continue
            if u.get("email") == exclude_email:
                continue
            full = sa.list_users(email=u["email"])[0]
            if not cls._has_master(full.get("user_permissions") or []):
                return u
        return None

    @staticmethod
    def _permission_names(email):
        # Read the user's currently-granted team permissions from the live
        # list_users response. This is the source of truth for whether a
        # grant/revoke actually took effect on the backend.
        return {
            p["name"]
            for p in (sa.list_users(email=email)[0].get("user_permissions") or [])
        }

    @classmethod
    def _includes(cls, names, *fragments):
        # True if some granted permission name contains every fragment. Uses
        # fragment matching so assertions are robust to the backend rendering
        # names with a curly apostrophe.
        return any(all(f in n for f in fragments) for n in names)

    def _check_permissions_granted(self, user_email, permission: str):
        user = sa.list_users(email=user_email)[0]
        user_permissions = [i["name"] for i in user.get("user_permissions")]
        assert permission in user_permissions

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
            self._check_permissions_granted(self.scapegoat['email'], self.PERMISSION)

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
            self._check_permissions_granted(self.scapegoat["email"], self.PERMISSION)

    def test_grant_all_permissions_wildcard(self):
        # "*" grants every permission available for the contributor role,
        # including the "Manage Contributors' permissions" master. With the
        # declarative setpermissions endpoint this is reversible, so it runs on
        # the shared scapegoat and is cleaned up by _reset().
        email = self.scapegoat["email"]
        with self.assertLogs("sa", level="INFO") as cm:
            sa.grant_team_user_permissions(permissions="*", user=email)
        success = [
            o for o in cm.output if o.startswith("INFO:sa:Successfully granted [")
        ]
        self.assertTrue(success, f"expected success log, got {cm.output}")
        line = success[0]
        for key in (
            "Manage Contributors",
            "Invite Contributors to team",
            "Remove Contributors from team",
            "Access Workload management",
        ):
            self.assertIn(key, line)
        granted = self._permission_names(email)
        self.assertEqual(granted, self._contributor_permission_names())
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
                f"User already has [{self.PERMISSION}] permission(s) granted." in joined
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

    def test_revoke_all_permissions_wildcard(self):
        # revoke "*" clears every permission the user currently holds. The
        # scapegoat never holds the (irreversible) master, so this is fully
        # reversible and runs idempotently on the shared scapegoat.
        email = self.scapegoat["email"]
        sa.grant_team_user_permissions(
            permissions=[self.PERMISSION, self.CURLY_PERMISSION],
            user=email,
        )
        granted = {
            p["name"]
            for p in (sa.list_users(email=email)[0].get("user_permissions") or [])
        }
        self.assertTrue(granted, "setup failed: permissions were not granted")
        with self.assertLogs("sa", level="INFO") as cm:
            sa.revoke_team_user_permissions(permissions="*", user=email)
        success = [
            o for o in cm.output if o.startswith("INFO:sa:Successfully revoked [")
        ]
        self.assertTrue(success, f"expected success log, got {cm.output}")
        remaining = {
            p["name"]
            for p in (sa.list_users(email=email)[0].get("user_permissions") or [])
        }
        self.assertEqual(remaining, set())

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
                sa.list_users(email=self.scapegoat["email"])[0].get("user_permissions")
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
        # contributor permissions. Reversible via setpermissions, so it runs on
        # the shared scapegoat and is cleaned up by _reset().
        email = self.scapegoat["email"]
        with self.assertLogs("sa", level="INFO") as cm:
            sa.grant_team_user_permissions(
                permissions=["Manage Contributors' permissions"],
                user=email,
            )
        success = [
            o for o in cm.output if o.startswith("INFO:sa:Successfully granted [")
        ]
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
        self.assertEqual(
            self._permission_names(email), self._contributor_permission_names()
        )

    def test_revoke_master_permission(self):
        # The master is now removable: revoking it drops the master while the
        # other contributor permissions it implied remain granted.
        email = self.scapegoat["email"]
        sa.grant_team_user_permissions(
            permissions=["Manage Contributors' permissions"], user=email
        )
        self.assertTrue(
            self._has_master([{"name": n} for n in self._permission_names(email)])
        )
        with self.assertLogs("sa", level="INFO") as cm:
            sa.revoke_team_user_permissions(
                permissions=["Manage Contributors' permissions"], user=email
            )
        success = [
            o for o in cm.output if o.startswith("INFO:sa:Successfully revoked [")
        ]
        self.assertTrue(success, f"expected success log, got {cm.output}")
        names = self._permission_names(email)
        self.assertFalse(
            self._has_master([{"name": n} for n in names]),
            f"master should be revoked, got {names}",
        )
        # Other members that the master implied remain granted.
        self.assertTrue(
            self._includes(names, "Invite Contributors to team"),
            f"members should remain after revoking the master, got {names}",
        )

    def test_revoke_blocked_while_manage_enabled(self):
        # While "Manage Contributors' permissions" is enabled it implies every
        # member, so an individual member cannot be revoked; the SDK reports the
        # "revoke Manage Contributors' permissions first" failure. Reversible,
        # so it runs on the scapegoat.
        email = self.scapegoat["email"]
        sa.grant_team_user_permissions(
            permissions=["Manage Contributors' permissions"], user=email
        )
        self.assertTrue(
            self._has_master([{"name": n} for n in self._permission_names(email)]),
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
        # The member is still present (revoke was blocked).
        self.assertTrue(
            self._includes(
                self._permission_names(email), "Remove Contributors from team"
            )
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
            for p in (
                sa.list_users(email=self.scapegoat["email"])[0].get("user_permissions")
                or []
            )
        }
        self.assertTrue(
            any(
                "View Contributors" in n and "custom field values" in n for n in granted
            ),
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
        success = [
            o for o in cm.output if o.startswith("INFO:sa:Successfully revoked [")
        ]
        self.assertTrue(success, f"expected success log, got {cm.output}")
        joined = "\n".join(success)
        self.assertIn("View Contributors", joined)
        self.assertIn("Edit Contributors", joined)
        remaining = {
            p["name"]
            for p in (
                sa.list_users(email=self.scapegoat["email"])[0].get("user_permissions")
                or []
            )
        }
        self.assertFalse(
            any("custom field values" in n for n in remaining),
            f"expected both custom-field-value permissions revoked, got {remaining}",
        )

    # ---- actual permission state verified via list_users ----------------

    def test_grant_actually_sets_permission(self):
        # Grant must actually set the permission on the backend, confirmed by
        # reading user_permissions back from list_users (not just the log).
        email = self.scapegoat["email"]
        self.assertNotIn(
            self.PERMISSION,
            self._permission_names(email),
            "precondition: permission must not be set before grant",
        )
        sa.grant_team_user_permissions(permissions=[self.PERMISSION], user=email)
        self.assertIn(
            self.PERMISSION,
            self._permission_names(email),
            "grant did not actually set the permission",
        )

    def test_revoke_actually_unsets_permission(self):
        # Revoke must actually clear the permission on the backend, confirmed
        # by reading user_permissions back from list_users.
        email = self.scapegoat["email"]
        sa.grant_team_user_permissions(permissions=[self.PERMISSION], user=email)
        self.assertIn(
            self.PERMISSION,
            self._permission_names(email),
            "setup failed: permission was not granted",
        )
        sa.revoke_team_user_permissions(permissions=[self.PERMISSION], user=email)
        self.assertNotIn(
            self.PERMISSION,
            self._permission_names(email),
            "revoke did not actually unset the permission",
        )

    def test_grant_edit_custom_fields_grant_cascade_sets_view(self):
        # Granting "Edit ... custom field values" must also set "View ...
        # custom field values" (grant cascade), verified against the live
        # user_permissions state, not just the success log.
        email = self.scapegoat["email"]
        sa.grant_team_user_permissions(
            permissions=[self.EDIT_CUSTOM_FIELDS], user=email
        )
        names = self._permission_names(email)
        self.assertTrue(
            self._includes(names, "Edit Contributors", "custom field values"),
            f"Edit permission not set, got {names}",
        )
        self.assertTrue(
            self._includes(names, "View Contributors", "custom field values"),
            f"grant cascade did not set View, got {names}",
        )

    def test_grant_edit_when_view_already_granted_leaves_both_set(self):
        # When the grant cascade's dependent ("View ... custom field values")
        # is already granted, granting "Edit ... custom field values" must
        # still leave both set: the already-granted dependent is a no-op, not
        # a failure that unsets state. Verified via live user_permissions.
        email = self.scapegoat["email"]
        sa.grant_team_user_permissions(
            permissions=[self.VIEW_CUSTOM_FIELDS], user=email
        )
        self.assertTrue(
            self._includes(
                self._permission_names(email),
                "View Contributors",
                "custom field values",
            ),
            "setup failed: View was not granted",
        )
        sa.grant_team_user_permissions(
            permissions=[self.EDIT_CUSTOM_FIELDS], user=email
        )
        names = self._permission_names(email)
        self.assertTrue(
            self._includes(names, "Edit Contributors", "custom field values"),
            f"Edit permission not set, got {names}",
        )
        self.assertTrue(
            self._includes(names, "View Contributors", "custom field values"),
            f"View should remain set after granting Edit, got {names}",
        )
