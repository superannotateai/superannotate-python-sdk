"""Unit tests for :class:`UpdateUserPermissionUseCase`.

These exercise the client-side business rules for
``SAClient.grant_team_user_permissions`` / ``revoke_team_user_permissions``
without a live backend, using a fake service provider whose permission data
mirrors the real ``teamUser`` permission groups:

    Team contributor permissions (ids 19-25)
        19  Manage Contributors' permissions   (master)
        20  Invite Contributors to team
        21  Remove Contributors from team
        22  View Contributors' scores
        23  View Contributors' custom field values
        24  Edit Contributors' custom field values
        25  Access Workload management

    Team admin permissions (ids 26-27)
        26  View SDK Token
        27  Access Orchestrate
"""
from unittest import TestCase

from src.superannotate.lib.core.entities.work_managament import WMUserTypeEnum
from src.superannotate.lib.core.reporter import Reporter
from src.superannotate.lib.core.usecases.work_management import (
    UpdateUserPermissionUseCase,
)
from src.superannotate.lib.infrastructure.utils import UserPermissionCache

CONTRIBUTOR_PERMS = {
    19: "Manage Contributors’ permissions",
    20: "Invite Contributors to team",
    21: "Remove Contributors from team",
    22: "View Contributors’ scores",
    23: "View Contributors’ custom field values",
    24: "Edit Contributors’ custom field values",
    25: "Access Workload management",
}
ADMIN_PERMS = {
    26: "View SDK Token",
    27: "Access Orchestrate",
}
ALL_PERMS = {**CONTRIBUTOR_PERMS, **ADMIN_PERMS}
GROUPS = {
    "Team contributor permissions": CONTRIBUTOR_PERMS,
    "Team admin permissions": ADMIN_PERMS,
}


def _normalize(name: str) -> str:
    return name.replace("’", "'").replace("‘", "'").lower()


class _FakeTeamUser:
    def __init__(self, id_: int, role: WMUserTypeEnum, email: str):
        self.id = id_
        self.role = role
        self.email = email


class _FakeWorkManagementService:
    """Models the permissions endpoint: only permissions whose state actually
    changes are echoed back under ``userPermissions`` (mirrors the real API,
    which silently ignores permissions already in the requested state)."""

    def __init__(self, granted):
        self.granted = set(granted)
        self.calls = []

    def edit_team_user_permissions(
        self, contributor_ids, permission_ids, operation, chunk_size=100
    ):
        self.calls.append((list(contributor_ids), list(permission_ids), operation))
        contributor_id = contributor_ids[0]
        affected = []
        for pid in permission_ids:
            if operation == "grant" and pid not in self.granted:
                self.granted.add(pid)
                affected.append(pid)
            elif operation == "revoke" and pid in self.granted:
                self.granted.discard(pid)
                affected.append(pid)
        entry = {
            "id": contributor_id,
            "userPermissions": [{"id": pid} for pid in affected],
        }
        section = "add" if operation == "grant" else "remove"
        return {"add": [], "remove": [], section: [entry]}


class _FakeServiceProvider:
    def __init__(self, granted=(), groups=None, name_by_id=None):
        self.work_management = _FakeWorkManagementService(granted)
        self._groups = groups if groups is not None else GROUPS
        self._name_by_id = name_by_id if name_by_id is not None else ALL_PERMS

    def get_team_user_permission_id_name_map(self):
        return dict(self._name_by_id)

    def get_team_user_permission_groups(self):
        return {name: dict(perms) for name, perms in self._groups.items()}

    def get_team_user_permission_id(self, name):
        target = _normalize(name)
        for pid, pname in self._name_by_id.items():
            if _normalize(pname) == target:
                return pid
        return None


class TestUpdateUserPermissionUseCase(TestCase):
    EMAIL = "contributor@superannotate.com"

    def _run(
        self,
        permissions,
        operation,
        granted=(),
        role=WMUserTypeEnum.Contributor,
        user=None,
        groups=None,
        name_by_id=None,
    ):
        reporter = Reporter()
        service_provider = _FakeServiceProvider(
            granted=granted, groups=groups, name_by_id=name_by_id
        )
        team_user = _FakeTeamUser(id_=101, role=role, email=self.EMAIL)
        resolver = (lambda _: [team_user]) if user is not False else (lambda _: [])
        use_case = UpdateUserPermissionUseCase(
            reporter=reporter,
            user=user if isinstance(user, (int, str)) else self.EMAIL,
            permissions=permissions,
            operation=operation,
            service_provider=service_provider,
            user_resolver=resolver,
        )
        response = use_case.execute()
        return response, reporter, service_provider

    @staticmethod
    def _message(reporter, prefix):
        for msg in reporter.info_messages:
            if msg.startswith(prefix):
                return msg
        return None

    # ---- success / failure logging -------------------------------------

    def test_grant_single_permission_success(self):
        response, reporter, sp = self._run(
            ["Invite Contributors to team"], "grant"
        )
        self.assertFalse(response.errors)
        self.assertEqual(
            self._message(reporter, "Successfully granted"),
            f"Successfully granted [Invite Contributors to team] "
            f"permission(s) for user: {self.EMAIL}.",
        )
        self.assertIsNone(self._message(reporter, "Could not grant"))
        self.assertEqual(sp.work_management.calls, [([101], [20], "grant")])

    def test_grant_already_granted_logs_failure(self):
        _, reporter, _ = self._run(
            ["Invite Contributors to team"], "grant", granted={20}
        )
        self.assertIsNone(self._message(reporter, "Successfully granted"))
        failure = self._message(reporter, "Could not grant")
        self.assertIsNotNone(failure)
        self.assertIn(
            "User already has [Invite Contributors to team] permission(s) granted.",
            failure,
        )

    def test_revoke_single_permission_success(self):
        _, reporter, _ = self._run(
            ["Invite Contributors to team"], "revoke", granted={20}
        )
        self.assertEqual(
            self._message(reporter, "Successfully revoked"),
            f"Successfully revoked [Invite Contributors to team] "
            f"permission(s) for user: {self.EMAIL}.",
        )

    def test_revoke_already_revoked_logs_failure(self):
        _, reporter, _ = self._run(["Invite Contributors to team"], "revoke")
        failure = self._message(reporter, "Could not revoke")
        self.assertIsNotNone(failure)
        self.assertIn(
            "[Invite Contributors to team] permission(s) were already revoked "
            "for the user.",
            failure,
        )

    # ---- cascades ------------------------------------------------------

    def test_grant_master_cascades_all_contributor_permissions(self):
        _, reporter, sp = self._run(
            ["Manage Contributors' permissions"], "grant"
        )
        # backend receives the master first, then every dependent permission
        self.assertEqual(
            sp.work_management.calls,
            [([101], [19, 20, 21, 22, 23, 24, 25], "grant")],
        )
        success = self._message(reporter, "Successfully granted")
        self.assertIsNotNone(success)
        for fragment in (
            "Manage Contributors",
            "Invite Contributors to team",
            "Remove Contributors from team",
            "View Contributors’ scores",
            "View Contributors’ custom field values",
            "Edit Contributors’ custom field values",
            "Access Workload management",
        ):
            self.assertIn(fragment, success)
        self.assertEqual(sp.work_management.granted, {19, 20, 21, 22, 23, 24, 25})

    def test_grant_master_cascade_derived_from_live_group_data(self):
        # The master cascade is derived from the permission-groups response,
        # not hardcoded. When a contributor permission is absent for the team
        # (here id 25 "Access Workload management"), granting the master must
        # cascade only to the permissions that actually exist.
        contributor_perms = {
            19: "Manage Contributors’ permissions",
            20: "Invite Contributors to team",
            21: "Remove Contributors from team",
            22: "View Contributors’ scores",
            23: "View Contributors’ custom field values",
            24: "Edit Contributors’ custom field values",
        }
        groups = {
            "Team contributor permissions": contributor_perms,
            "Team admin permissions": ADMIN_PERMS,
        }
        _, _, sp = self._run(
            ["Manage Contributors' permissions"],
            "grant",
            groups=groups,
            name_by_id={**contributor_perms, **ADMIN_PERMS},
        )
        self.assertEqual(
            sp.work_management.calls,
            [([101], [19, 20, 21, 22, 23, 24], "grant")],
        )
        self.assertEqual(sp.work_management.granted, {19, 20, 21, 22, 23, 24})

    def test_grant_edit_custom_fields_cascades_view(self):
        _, reporter, sp = self._run(
            ["Edit Contributors' custom field values"], "grant"
        )
        self.assertEqual(
            sp.work_management.calls, [([101], [24, 23], "grant")]
        )
        success = self._message(reporter, "Successfully granted")
        self.assertIn("Edit Contributors’ custom field values", success)
        self.assertIn("View Contributors’ custom field values", success)

    def test_revoke_view_custom_fields_cascades_edit(self):
        _, reporter, sp = self._run(
            ["View Contributors' custom field values"],
            "revoke",
            granted={23, 24},
        )
        self.assertEqual(
            sp.work_management.calls, [([101], [23, 24], "revoke")]
        )
        success = self._message(reporter, "Successfully revoked")
        self.assertIn("View Contributors’ custom field values", success)
        self.assertIn("Edit Contributors’ custom field values", success)
        self.assertEqual(sp.work_management.granted, set())

    # ---- "*" is scoped to the user's role ------------------------------

    def test_wildcard_contributor_role_grants_only_contributor_permissions(self):
        _, reporter, sp = self._run("*", "grant", role=WMUserTypeEnum.Contributor)
        _, sent, _ = sp.work_management.calls[0]
        self.assertEqual(set(sent), set(CONTRIBUTOR_PERMS))
        self.assertEqual(sent[0], 19, "master permission must be sent first")
        self.assertFalse(set(sent) & set(ADMIN_PERMS))

    def test_wildcard_admin_role_grants_only_admin_permissions(self):
        _, reporter, sp = self._run("*", "grant", role=WMUserTypeEnum.TeamAdmin)
        _, sent, _ = sp.work_management.calls[0]
        self.assertEqual(set(sent), set(ADMIN_PERMS))
        self.assertFalse(set(sent) & set(CONTRIBUTOR_PERMS))
        success = self._message(reporter, "Successfully granted")
        self.assertIn("View SDK Token", success)
        self.assertIn("Access Orchestrate", success)

    # ---- role mismatch (admin perm <-> contributor) ---------------------

    def test_grant_admin_permission_for_contributor_logs_role_mismatch(self):
        # An admin-only permission requested for a contributor must not be
        # sent to the backend; the SDK reports a role-mismatch failure.
        _, reporter, sp = self._run(["View SDK Token"], "grant")
        self.assertEqual(sp.work_management.calls, [])
        failure = self._message(reporter, "Could not grant")
        self.assertIsNotNone(failure)
        self.assertIn("[View SDK Token]", failure)
        self.assertIn(
            "User role does not allow [View SDK Token] permission(s).",
            failure,
        )
        self.assertIsNone(self._message(reporter, "Successfully granted"))

    def test_grant_contributor_permission_for_admin_logs_role_mismatch(self):
        # A contributor-only permission requested for an admin must not be
        # sent to the backend; the SDK reports a role-mismatch failure.
        _, reporter, sp = self._run(
            ["Invite Contributors to team"], "grant", role=WMUserTypeEnum.TeamAdmin
        )
        self.assertEqual(sp.work_management.calls, [])
        failure = self._message(reporter, "Could not grant")
        self.assertIsNotNone(failure)
        self.assertIn("[Invite Contributors to team]", failure)
        self.assertIn(
            "User role does not allow [Invite Contributors to team] permission(s).",
            failure,
        )
        self.assertIsNone(self._message(reporter, "Successfully granted"))

    def test_grant_mixed_valid_and_role_mismatch_grants_valid_only(self):
        # A valid contributor permission mixed with a role-invalid admin one
        # must grant the valid one and report the admin one as a failure
        # (the role-invalid permission is not sent, so it cannot poison the
        # backend's all-or-nothing batch).
        _, reporter, sp = self._run(
            ["Invite Contributors to team", "View SDK Token"], "grant"
        )
        self.assertEqual(sp.work_management.calls, [([101], [20], "grant")])
        self.assertIn(
            "Invite Contributors to team",
            self._message(reporter, "Successfully granted"),
        )
        failure = self._message(reporter, "Could not grant")
        self.assertIsNotNone(failure)
        self.assertIn("[View SDK Token]", failure)

    # ---- name resolution -----------------------------------------------

    def test_invalid_permission_logs_failure_and_skips_backend(self):
        _, reporter, sp = self._run(["NonExistentPermission"], "grant")
        self.assertEqual(sp.work_management.calls, [])
        failure = self._message(reporter, "Could not grant")
        self.assertIsNotNone(failure)
        self.assertIn("[NonExistentPermission]", failure)
        self.assertIn("Provided permission(s) were invalid.", failure)

    def test_mixed_valid_and_invalid_logs_both(self):
        _, reporter, _ = self._run(
            ["Invite Contributors to team", "NonExistentPermission"], "grant"
        )
        self.assertIn(
            "Invite Contributors to team",
            self._message(reporter, "Successfully granted"),
        )
        self.assertIn(
            "NonExistentPermission", self._message(reporter, "Could not grant")
        )

    def test_case_insensitive_permission_name(self):
        _, reporter, sp = self._run(["invite contributors to team"], "grant")
        self.assertEqual(sp.work_management.calls, [([101], [20], "grant")])
        self.assertIsNotNone(self._message(reporter, "Successfully granted"))

    def test_straight_apostrophe_resolves_to_canonical_name(self):
        # User supplies a straight apostrophe; backend stores a curly one.
        _, reporter, sp = self._run(["View Contributors' scores"], "grant")
        self.assertEqual(sp.work_management.calls, [([101], [22], "grant")])
        self.assertEqual(
            self._message(reporter, "Successfully granted"),
            f"Successfully granted [View Contributors’ scores] "
            f"permission(s) for user: {self.EMAIL}.",
        )

    def test_duplicate_permission_names_deduplicated(self):
        _, _, sp = self._run(
            ["Invite Contributors to team", "invite contributors to team"],
            "grant",
        )
        self.assertEqual(sp.work_management.calls, [([101], [20], "grant")])

    # ---- error paths ---------------------------------------------------

    def test_empty_permissions_returns_error(self):
        response, reporter, sp = self._run([], "grant")
        self.assertEqual(response.errors, "Permission(s) cannot be empty.")
        self.assertEqual(reporter.info_messages, [])
        self.assertEqual(sp.work_management.calls, [])

    def test_unknown_user_returns_error(self):
        response, reporter, sp = self._run(
            ["Invite Contributors to team"], "grant", user=False
        )
        self.assertEqual(response.errors, "User not found.")
        self.assertEqual(reporter.info_messages, [])
        self.assertEqual(sp.work_management.calls, [])


class TestUserPermissionNameNormalization(TestCase):
    def test_normalizes_curly_apostrophe_and_case(self):
        self.assertEqual(
            UserPermissionCache._normalize_name("View Contributors’ SCORES"),
            "view contributors' scores",
        )

    def test_left_and_right_single_quotes_normalized(self):
        self.assertEqual(
            UserPermissionCache._normalize_name("A‘b’c"), "a'b'c"
        )
