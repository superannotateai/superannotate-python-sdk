from unittest import skip
from unittest import skipIf
from unittest import skipUnless
from unittest import TestCase

from lib.core import TEAM_USER_PERMISSION_DEPRECATED_IDS
from lib.core.entities.context import TokenScope
from lib.core.exceptions import AppException
from src.superannotate import SAClient

sa = SAClient()

#: A team-scoped API key authenticates as the team itself - there is no user behind
#: it - so the backend does not let it change a team admin's permissions: the write
#: is accepted but nothing is applied, and the SDK reports the attempt as a failure.
#: A personal (team-user) API key and a legacy team-owner token both authenticate as
#: a user and may update team admin permissions, which is what the bulk of this
#: module asserts. The suite therefore picks its expectations from the token the
#: client was built with.
IS_TEAM_KEY = sa.controller.token_context.scope == TokenScope.TEAM
TEAM_KEY_ONLY = "requires a team-scoped API key"
USER_KEY_ONLY = "requires a personal (team-user) API key or a legacy token"
#: Reason line the SDK adds to every permission-update failure, and the only one
#: that applies when the token itself is what blocked the update.
INSUFFICIENT_KEY_REASON = (
    "The API key used does not have sufficient permissions to perform this action."
)


class TeamAdminPermissionsMixin:
    """Permission names and read-only helpers shared by both token flavours."""

    # "Access Orchestrate" (id 27) is apostrophe-free, so exact log assertions on
    # it are stable regardless of the backend's curly/straight rendering. All
    # admin permissions are reversible.
    PERMISSION = "Access Orchestrate"
    # Admin permission whose canonical name contains an apostrophe.
    OTHER_PERMISSION = "Revoke members' personal API keys"
    # The team-admin master (id 29): granting it grants every other admin
    # permission, and no admin permission can be revoked while it is granted.
    MASTER_PERMISSION = "Access team API keys"
    # A contributor-only permission; granting it to an admin must be rejected.
    CONTRIBUTOR_PERMISSION = "Invite Contributors to team"

    scapegoat: dict

    @classmethod
    def _admin_permission_names(cls):
        # The grantable team-admin permissions for this team, so the wildcard
        # assertions and cleanup don't hardcode a count that changes whenever an
        # admin permission is added or renamed. Deprecated ids come from the
        # source constant so the test cannot drift from the implementation.
        groups = sa.controller.service_provider.get_team_user_permission_groups()
        for name, perms in groups.items():
            if "admin" in name.lower():
                return {
                    n
                    for pid, n in perms.items()
                    if pid not in TEAM_USER_PERMISSION_DEPRECATED_IDS
                }
        return set()

    @classmethod
    def _confirmed_admins(cls):
        return [
            u
            for u in sa.list_users()
            if u.get("state") == "Confirmed" and u.get("role") in ("TeamAdmin")
        ]

    @classmethod
    def _user_permissions(cls):
        return (
            sa.list_users(email=cls.scapegoat["email"])[0].get("user_permissions") or []
        )

    @classmethod
    def _granted(cls):
        return {p["name"] for p in cls._user_permissions()}

    @classmethod
    def _granted_ids(cls):
        return {p["id"] for p in cls._user_permissions()}


@skipIf(IS_TEAM_KEY, USER_KEY_ONLY)
class TestTeamAdminUserPermissions(TeamAdminPermissionsMixin, TestCase):
    """Team admin permission updates through a token that acts as a user."""

    @classmethod
    def setUpClass(cls, *args, **kwargs) -> None:
        cls.scapegoat = cls._find_admin()
        # The scapegoat may be a real admin holding real permissions (there is
        # not always a permission-free admin to borrow), so snapshot the exact
        # ids and put the account back in tearDownClass. _find_admin guarantees
        # every held permission can actually be written back.
        cls.original_permission_ids = cls._granted_ids()
        cls._cleanup()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._restore()

    @classmethod
    def _restore(cls):
        # Restore by id through the declarative endpoint rather than by
        # re-granting names: a held permission may no longer be grantable (e.g.
        # "View SDK Token"), so a name-based grant could not put it back.
        sa.controller.service_provider.work_management.set_team_user_permissions(
            contributor_id=sa.list_users(email=cls.scapegoat["email"])[0]["id"],
            permission_ids=list(cls.original_permission_ids),
        )

    @classmethod
    def _find_admin(cls):
        """Pick an admin whose permission state the suite can safely restore.

        The tests clear the borrowed account down to a known baseline, so it must
        be possible to put every permission back afterwards. Permissions in
        ``TEAM_USER_PERMISSION_DEPRECATED_IDS`` cannot be written at all (the
        backend silently drops them even through the declarative endpoint), so
        clearing an account that holds one is irreversible - never borrow it.
        Prefer an admin with no permissions, then any whose set is restorable.
        """
        candidates = []
        for u in cls._confirmed_admins():
            ids = {
                p["id"]
                for p in (
                    sa.list_users(email=u["email"])[0].get("user_permissions") or []
                )
            }
            if ids & TEAM_USER_PERMISSION_DEPRECATED_IDS:
                continue
            candidates.append((len(ids), u))
        if not candidates:
            raise RuntimeError(
                "No Confirmed team admin available whose permissions can be "
                "restored after the test run. Admins holding "
                f"{sorted(TEAM_USER_PERMISSION_DEPRECATED_IDS)} are skipped "
                "because those permissions cannot be granted back."
            )
        candidates.sort(key=lambda candidate: candidate[0])
        return candidates[0][1]

    @classmethod
    def _cleanup(cls):
        # revoke "*" clears the whole admin set in one call, master included.
        # Revoking name-by-name would deadlock: while the master is granted no
        # sibling can be revoked, so the outcome would depend on iteration order.
        try:
            sa.revoke_team_user_permissions(
                permissions="*",
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

    def test_grant_curly_apostrophe_input_resolves(self):
        # The canonical name uses a straight apostrophe; a curly one must still
        # resolve and be reported back under the canonical name.
        with self.assertLogs("sa", level="INFO") as cm:
            sa.grant_team_user_permissions(
                permissions=["Revoke members’ personal API keys"],
                user=self.scapegoat["email"],
            )
            joined = "\n".join(cm.output)
            self.assertIn(
                f"Successfully granted [{self.OTHER_PERMISSION}] permission(s) "
                f"for user: {self.scapegoat['email']}.",
                joined,
            )
        self.assertIn(self.OTHER_PERMISSION, self._granted())

    def test_grant_lowercase_input_resolves(self):
        with self.assertLogs("sa", level="INFO") as cm:
            sa.grant_team_user_permissions(
                permissions=[self.PERMISSION.lower()],
                user=self.scapegoat["email"],
            )
            self.assertEqual(
                cm.output[0],
                f"INFO:sa:Successfully granted [{self.PERMISSION}] permission(s) "
                f"for user: {self.scapegoat['email']}.",
            )

    def test_grant_all_permissions_wildcard(self):
        # "*" resolves to every grantable permission of the admin role. Fully
        # reversible, so it can be exercised idempotently.
        expected = self._admin_permission_names()
        self.assertTrue(expected, "no team admin permissions reported by the backend")
        with self.assertLogs("sa", level="INFO") as cm:
            sa.grant_team_user_permissions(
                permissions="*",
                user=self.scapegoat["email"],
            )
        success = [
            o for o in cm.output if o.startswith("INFO:sa:Successfully granted [")
        ]
        self.assertTrue(success, f"expected success log, got {cm.output}")
        line = success[0]
        self.assertIn(f"permission(s) for user: {self.scapegoat['email']}.", line)
        for name in expected:
            self.assertIn(name, line)
        # The deprecated permission is skipped, so there is no failure block.
        self.assertFalse(
            [o for o in cm.output if o.startswith("INFO:sa:Could not grant [")],
            f"unexpected failure log: {cm.output}",
        )
        self.assertEqual(self._granted(), expected)

    # ---- the team-admin master: "Access team API keys" -------------------

    def test_grant_master_cascades_to_whole_admin_group(self):
        # Granting the master must grant every other grantable admin permission.
        expected = self._admin_permission_names()
        with self.assertLogs("sa", level="INFO") as cm:
            sa.grant_team_user_permissions(
                permissions=[self.MASTER_PERMISSION],
                user=self.scapegoat["email"],
            )
        success = [
            o for o in cm.output if o.startswith("INFO:sa:Successfully granted [")
        ]
        self.assertTrue(success, f"expected success log, got {cm.output}")
        for name in expected:
            self.assertIn(name, success[0])
        # No spurious failure for the deprecated permission.
        self.assertFalse(
            [o for o in cm.output if o.startswith("INFO:sa:Could not grant [")],
            f"unexpected failure log: {cm.output}",
        )
        self.assertEqual(self._granted(), expected)

    def test_revoke_blocked_while_master_enabled(self):
        # While the master is granted it implies every admin permission, so an
        # individual one cannot be revoked; the SDK reports the admin-master
        # failure and the state is left untouched.
        email = self.scapegoat["email"]
        sa.grant_team_user_permissions(permissions=[self.MASTER_PERMISSION], user=email)
        before = self._granted()
        self.assertIn(
            self.MASTER_PERMISSION, before, "setup failed: master not granted"
        )
        with self.assertLogs("sa", level="INFO") as cm:
            sa.revoke_team_user_permissions(permissions=[self.PERMISSION], user=email)
        failure = [o for o in cm.output if o.startswith("INFO:sa:Could not revoke [")]
        self.assertTrue(failure, f"expected failure log, got {cm.output}")
        joined = "\n".join(failure)
        self.assertIn(
            f"If {self.MASTER_PERMISSION} is granted, it must be revoked before "
            f"[{self.PERMISSION}] can be revoked for this user.",
            joined,
        )
        # The hint stays scoped to the admin group.
        self.assertNotIn("Manage Contributors", joined)
        # Nothing was revoked.
        self.assertEqual(self._granted(), before)

    def test_revoke_master_leaves_siblings_granted(self):
        # The master itself is revocable; the permissions it implied remain.
        email = self.scapegoat["email"]
        sa.grant_team_user_permissions(permissions=[self.MASTER_PERMISSION], user=email)
        with self.assertLogs("sa", level="INFO") as cm:
            sa.revoke_team_user_permissions(
                permissions=[self.MASTER_PERMISSION], user=email
            )
            self.assertEqual(
                cm.output[0],
                f"INFO:sa:Successfully revoked [{self.MASTER_PERMISSION}] "
                f"permission(s) for user: {email}.",
            )
        remaining = self._granted()
        self.assertNotIn(self.MASTER_PERMISSION, remaining)
        self.assertEqual(
            remaining, self._admin_permission_names() - {self.MASTER_PERMISSION}
        )

    def test_revoke_wildcard_clears_master_and_siblings(self):
        email = self.scapegoat["email"]
        sa.grant_team_user_permissions(permissions=[self.MASTER_PERMISSION], user=email)
        self.assertTrue(self._granted(), "setup failed: nothing granted")
        with self.assertLogs("sa", level="INFO") as cm:
            sa.revoke_team_user_permissions(permissions="*", user=email)
        self.assertTrue(
            [o for o in cm.output if o.startswith("INFO:sa:Successfully revoked [")],
            f"expected success log, got {cm.output}",
        )
        self.assertEqual(self._granted(), set())

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
            # The token is never the reason here, but it is one of the listed
            # possibilities on any failed grant.
            self.assertIn(INSUFFICIENT_KEY_REASON, joined)

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

    def test_revoke_all_permissions_wildcard(self):
        # revoke "*" clears every admin permission the user currently holds.
        # Admin permissions are fully reversible, so this is idempotent.
        email = self.scapegoat["email"]
        sa.grant_team_user_permissions(
            permissions=[self.PERMISSION, self.OTHER_PERMISSION],
            user=email,
        )
        granted = {
            p["name"]
            for p in (sa.list_users(email=email)[0].get("user_permissions") or [])
        }
        self.assertEqual(granted, {self.PERMISSION, self.OTHER_PERMISSION})
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
            self.assertIn(
                f"Could not revoke [{self.PERMISSION}] permission(s) "
                f"for user: {self.scapegoat['email']}.",
                joined,
            )
            self.assertIn(
                f"[{self.PERMISSION}] permission(s) were already revoked for the user.",
                joined,
            )
            self.assertIn(INSUFFICIENT_KEY_REASON, joined)

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
                sa.list_users(email=self.scapegoat["email"])[0].get("user_permissions")
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


@skipUnless(IS_TEAM_KEY, TEAM_KEY_ONLY)
class TestTeamAdminUserPermissionsWithTeamKey(TeamAdminPermissionsMixin, TestCase):
    """Team admin permission updates through a key that acts as the team.

    Only granting is refused: the backend accepts the write, applies nothing, and
    the SDK reports a failure whose possible reasons include the insufficient key.

    Revoking is *not* refused - a team key really does remove the permission (see
    ``test_revoke_of_a_held_permission_is_not_blocked``). That asymmetry makes any
    successful revoke a one-way door for this suite: the same key cannot grant the
    permission back afterwards, so nothing here revokes a permission the account
    actually holds. Every case below leaves the account untouched, which is what
    lets the class run without a restore step.
    """

    @classmethod
    def setUpClass(cls, *args, **kwargs) -> None:
        admins = cls._confirmed_admins()
        if not admins:
            raise RuntimeError("No Confirmed team admin available to test against.")
        cls.scapegoat = admins[0]

    def _assert_denied(self, operation: str, permissions, expected_names):
        """Run an update that the key is not allowed to make and check the log."""
        email = self.scapegoat["email"]
        before = self._granted()
        update = (
            sa.grant_team_user_permissions
            if operation == "grant"
            else sa.revoke_team_user_permissions
        )
        past = "granted" if operation == "grant" else "revoked"
        with self.assertLogs("sa", level="INFO") as cm:
            update(permissions=permissions, user=email)
        self.assertFalse(
            [o for o in cm.output if o.startswith(f"INFO:sa:Successfully {past} [")],
            f"nothing should have been {past} here, got {cm.output}",
        )
        failure = [
            o for o in cm.output if o.startswith(f"INFO:sa:Could not {operation} [")
        ]
        self.assertTrue(failure, f"expected failure log, got {cm.output}")
        joined = "\n".join(failure)
        self.assertIn(f"permission(s) for user: {email}.", joined)
        for name in expected_names:
            self.assertIn(name, joined)
        self.assertIn(INSUFFICIENT_KEY_REASON, joined)
        # The permission set is untouched.
        self.assertEqual(self._granted(), before)

    def _unheld_admin_permission(self):
        """An admin permission the account does not have, so the grant is real.

        Granting one it already holds would fail for a second reason ("already
        granted"), which would not prove the key was refused. The master is
        excluded as well: it cascades to the whole group, so the failure would be
        reported for every admin permission rather than for the requested one.
        """
        missing = self._admin_permission_names() - self._granted()
        missing -= {self.MASTER_PERMISSION}
        if not missing:
            self.skipTest(
                "the borrowed admin holds every non-master admin permission, so "
                "there is no grant left to be refused"
            )
        # Prefer the module's reference permission when it is available.
        return self.PERMISSION if self.PERMISSION in missing else sorted(missing)[0]

    def test_grant_permission_denied(self):
        permission = self._unheld_admin_permission()
        self._assert_denied("grant", [permission], [permission])

    def test_grant_by_user_id_denied(self):
        permission = self._unheld_admin_permission()
        team_user_id = sa.list_users(email=self.scapegoat["email"])[0]["id"]
        before = self._granted()
        with self.assertLogs("sa", level="INFO") as cm:
            sa.grant_team_user_permissions(permissions=[permission], user=team_user_id)
        joined = "\n".join(cm.output)
        self.assertIn(
            f"Could not grant [{permission}] permission(s) "
            f"for user: {self.scapegoat['email']}.",
            joined,
        )
        self.assertIn(INSUFFICIENT_KEY_REASON, joined)
        self.assertEqual(self._granted(), before)

    def test_grant_master_denied(self):
        # The master cascades to the whole admin group, so the failure names every
        # grantable admin permission: nothing changed, so nothing succeeded.
        self._assert_denied(
            "grant", [self.MASTER_PERMISSION], self._admin_permission_names()
        )

    def test_grant_wildcard_denied(self):
        self._assert_denied("grant", "*", self._admin_permission_names())

    @skip(
        "A team key can revoke: the backend applies it, and the same key cannot "
        "grant the permission back, so running this strips the borrowed admin for "
        "good. Unskip only against an account whose permissions are disposable."
    )
    def test_revoke_of_a_held_permission_is_not_blocked(self):
        # Documents the asymmetry rather than asserting the denial: granting is
        # refused for a team key, revoking is not.
        held = self._granted() & self._admin_permission_names()
        if not held:
            self.skipTest("the borrowed admin holds no revocable permission")
        permission = sorted(held)[0]
        with self.assertLogs("sa", level="INFO") as cm:
            sa.revoke_team_user_permissions(
                permissions=[permission], user=self.scapegoat["email"]
            )
        self.assertTrue(
            [o for o in cm.output if o.startswith("INFO:sa:Successfully revoked [")],
            f"expected the revoke to go through, got {cm.output}",
        )
        self.assertNotIn(permission, self._granted())

    def test_revoke_of_a_permission_not_held_reports_failure(self):
        # Safe to run: nothing is revoked, so nothing has to be granted back. The
        # key is one of the reasons offered for the failure.
        missing = self._admin_permission_names() - self._granted()
        if not missing:
            self.skipTest("the borrowed admin holds every admin permission")
        permission = sorted(missing)[0]
        self._assert_denied("revoke", [permission], [permission])

    def test_invalid_permission_still_reported_as_invalid(self):
        # Name resolution happens client-side, so it is unaffected by the token.
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

    def test_empty_permissions_raises(self):
        # Client-side validation, so it behaves the same for every token.
        for update in (
            sa.grant_team_user_permissions,
            sa.revoke_team_user_permissions,
        ):
            with self.assertRaisesRegex(
                AppException, r"Permission\(s\) cannot be empty\."
            ):
                update(permissions=[], user=self.scapegoat["email"])

    def test_unknown_user_raises(self):
        for update in (
            sa.grant_team_user_permissions,
            sa.revoke_team_user_permissions,
        ):
            with self.assertRaisesRegex(AppException, "User not found."):
                update(
                    permissions=[self.PERMISSION],
                    user="non_existent_admin@superannotate.com",
                )
