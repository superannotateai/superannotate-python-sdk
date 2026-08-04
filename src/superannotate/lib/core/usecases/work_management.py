from __future__ import annotations

from collections.abc import Callable
from typing import Literal

import lib.core as constants
from lib.core.entities.work_managament import WMUserTypeEnum
from lib.core.reporter import Reporter
from lib.core.response import Response
from lib.core.serviceproviders import BaseServiceProvider
from lib.core.usecases import BaseReportableUseCase

PermissionOperation = Literal["grant", "revoke"]

# Permission ids used by the cascade rules (see constants).
MASTER_IDS = frozenset(constants.TEAM_USER_PERMISSION_MASTERS)
DEPRECATED_IDS = constants.TEAM_USER_PERMISSION_DEPRECATED_IDS
CONTRIBUTOR_MASTER_ID = 19
# Master named in the revoke failure hint when the failed permissions cannot be
# traced back to a group (e.g. they are all unresolved names). Defaults to the
# contributor master, which is the pre-existing wording.
DEFAULT_MASTER_NAME = constants.TEAM_USER_PERMISSION_MASTERS[CONTRIBUTOR_MASTER_ID]


class UpdateUserPermissionUseCase(BaseReportableUseCase):
    """Grant or revoke team-user permissions for a single user.

    The backend endpoint (``teamusers/setpermissions``) is declarative: it
    replaces the user's whole permission set with the list we send. Grant and
    revoke are therefore implemented as read-modify-write on that set, while
    this use case keeps the business rules the endpoint does not enforce:

      - "*" resolves only to the permissions allowed for the user's role
        (a role-invalid permission makes the backend reject the whole set);
      - permission names are matched case- and apostrophe-insensitively;
      - documented cascades are mirrored client-side (see
        ``constants.TEAM_USER_PERMISSION_GRANT_CASCADE`` /
        ``TEAM_USER_PERMISSION_REVOKE_CASCADE``) because the backend does not
        auto-cascade;
      - each group's master permission (see
        ``constants.TEAM_USER_PERMISSION_MASTERS``: "Manage Contributors'
        permissions" for contributors, "Access team API keys" for admins)
        implies every other permission in its own group: whenever a master
        stays in the desired set we add the rest of its group (this also
        preserves the rule that a group's permissions cannot be revoked while
        its master is enabled);
      - permissions the backend no longer grants
        (``constants.TEAM_USER_PERMISSION_DEPRECATED_IDS``) are left out of
        ``"*"`` and of master cascades so they are not reported as failures;
      - per-permission success / failure is reported through the reporter.
    """

    def __init__(
        self,
        reporter: Reporter,
        user: int | str,
        permissions: list[str] | Literal["*"],
        operation: PermissionOperation,
        service_provider: BaseServiceProvider,
        user_resolver: Callable[[int | str], list],
    ):
        super().__init__(reporter)
        self._user = user
        self._permissions = permissions
        self._operation = operation
        self._service_provider = service_provider
        self._user_resolver = user_resolver

    def execute(self) -> Response:
        if not self._permissions:
            self._response.errors = "Permission(s) cannot be empty."
            return self._response

        team_users = self._user_resolver(self._user)
        if not team_users:
            self._response.errors = "User not found."
            return self._response

        team_user = team_users[0]
        name_by_id = self._service_provider.get_team_user_permission_id_name_map()
        groups = self._groups()
        current_ids = [
            p.id for p in (team_user.user_permissions or []) if p.id is not None
        ]

        resolved_ids, unresolved_names, role_mismatch_names = self._resolve_permissions(
            team_user.role, name_by_id, groups, current_ids
        )

        # The group that applies to this user's role. The master rules are scoped
        # to it so a permission the user holds from outside their role (stale
        # data after a role change) can never pull in another group's ids.
        role_group = (
            self._role_team_user_permission_map(team_user.role, name_by_id, groups)
            if groups
            else None
        )

        # The permissions we attempted to change (requested + cascade), used for
        # per-permission success / failure reporting.
        cascade = self._build_cascade(self._operation, groups, set(name_by_id))
        attempted_ids = self._cascade_team_permission_ids(resolved_ids, cascade)

        desired_ids = self._desired_permission_ids(
            current_ids, attempted_ids, role_group
        )

        # Skip the network round-trip when nothing would change.
        if set(desired_ids) == set(current_ids):
            new_state = set(current_ids)
        else:
            new_state = self._apply(team_user.id, desired_ids)

        self._log(
            current_ids,
            new_state,
            attempted_ids,
            unresolved_names,
            role_mismatch_names,
            team_user.email,
            role_group,
        )
        return self._response

    def _groups(self) -> dict[str, dict[int, str]] | None:
        try:
            return self._service_provider.get_team_user_permission_groups()
        except Exception:
            return None

    def _desired_permission_ids(
        self,
        current_ids: list[int],
        attempted_ids: list[int],
        role_group: dict[int, str] | None,
    ) -> list[int]:
        """Full permission set to send, derived from the current set.

        Grant unions the attempted ids into the current set; revoke subtracts
        them. The master invariant is applied last so that a set still holding
        the master keeps its whole group (and members cannot be revoked while
        the master is enabled).
        """
        current = set(current_ids)
        if self._operation == "grant":
            desired = current | set(attempted_ids)
        else:
            desired = current - set(attempted_ids)
        desired = self._apply_master_invariant(desired, role_group)
        return sorted(desired)

    @staticmethod
    def _group_master(perms: dict[int, str]) -> int | None:
        """The master permission id of a group, if the group has one."""
        return next((pid for pid in perms if pid in MASTER_IDS), None)

    @classmethod
    def _apply_master_invariant(
        cls, desired: set[int], role_group: dict[int, str] | None
    ) -> set[int]:
        """Re-add the role's permissions whenever its master stays granted.

        Applied to the desired set of every operation, this enforces both master
        rules at once: granting a master pulls in its whole group, and a group's
        permissions cannot be revoked while its master is still granted (the
        subtraction is undone here, so the desired set ends up unchanged and the
        revoke is reported as a failure).

        Only the group matching the user's role is considered, so a permission
        held from outside that role never drags in another group's ids.
        """
        if not role_group:
            return desired
        master_id = cls._group_master(role_group)
        if master_id is not None and master_id in desired:
            desired = desired | (set(role_group) - DEPRECATED_IDS)
        return desired

    def _apply(self, contributor_id: int, permission_ids: list[int]) -> set[int]:
        return set(
            self._service_provider.work_management.set_team_user_permissions(
                contributor_id=contributor_id,
                permission_ids=permission_ids,
            )
        )

    def _resolve_permissions(
        self,
        role: WMUserTypeEnum,
        name_by_id: dict[int, str],
        groups: dict[str, dict[int, str]] | None,
        current_perm_ids: list[int],
    ) -> tuple[list[int], list[str], list[str]]:
        # Permissions valid for the user's role. When the role groups cannot be
        # fetched this falls back to the full map, deferring role enforcement
        # to the backend.
        role_ids = set(
            self._role_team_user_permission_map(role, name_by_id, groups).keys()
        )
        if self._permissions == "*":
            if self._operation == "revoke":
                # revoke "*" clears the permissions the user currently holds
                # (including the master, now that it is removable). Resolve to
                # the held permissions so the desired set becomes empty.
                # Deprecated ids are not filtered here: a user who somehow holds
                # one should still be able to clear it.
                return [pid for pid in current_perm_ids if pid in role_ids], [], []
            # grant "*" skips permissions the backend no longer grants, and is
            # sorted so the reported order is deterministic.
            return sorted(role_ids - DEPRECATED_IDS), [], []

        resolved_ids: list[int] = []
        seen_ids: set[int] = set()
        unresolved_names: list[str] = []
        role_mismatch_names: list[str] = []
        for name in self._permissions:
            pid = self._service_provider.get_team_user_permission_id(name)
            if pid is None:
                unresolved_names.append(name)
            elif pid not in role_ids:
                # Valid permission name, but not allowed for this user's role
                # (e.g. an admin permission requested for a contributor, or
                # vice versa). Don't send it to the backend; report it as a
                # role-mismatch failure using the canonical name.
                role_mismatch_names.append(name_by_id[pid])
            elif pid not in seen_ids:
                resolved_ids.append(pid)
                seen_ids.add(pid)
        return resolved_ids, unresolved_names, role_mismatch_names

    @classmethod
    def _master_name(cls, role_group: dict[int, str] | None) -> str:
        """Canonical name of the master that governs this user's permissions.

        Keeps the revoke hint scoped to the user's role: a contributor is never
        told to revoke the admin master, and vice versa. Falls back to the
        contributor master when the role's group is unavailable.
        """
        if role_group:
            master_id = cls._group_master(role_group)
            if master_id is not None:
                return role_group[master_id]
        return DEFAULT_MASTER_NAME

    def _log(
        self,
        current_ids: list[int],
        new_state: set[int],
        attempted_ids: list[int],
        unresolved_names: list[str],
        role_mismatch_names: list[str],
        user_email: str,
        role_group: dict[int, str] | None = None,
    ) -> None:
        name_by_id = self._service_provider.get_team_user_permission_id_name_map()
        current = set(current_ids)
        # Permissions whose state actually changed in the intended direction.
        if self._operation == "grant":
            changed = new_state - current
        else:
            changed = current - new_state

        failed_ids = [pid for pid in attempted_ids if pid not in changed]
        succeeded_names = [name_by_id[pid] for pid in attempted_ids if pid in changed]
        failed_names = (
            [name_by_id[pid] for pid in failed_ids]
            + role_mismatch_names
            + unresolved_names
        )

        verb_inf = "grant" if self._operation == "grant" else "revoke"
        verb_past = "granted" if self._operation == "grant" else "revoked"

        if succeeded_names:
            self.reporter.log_info(
                f"Successfully {verb_past} [{', '.join(succeeded_names)}] "
                f"permission(s) for user: {user_email}."
            )
        if failed_names:
            failed_str = f"[{', '.join(failed_names)}]"
            if self._operation == "grant":
                reasons = (
                    f"- User already has {failed_str} permission(s) granted.\n"
                    f"- User role does not allow {failed_str} permission(s).\n"
                    f"- Provided permission(s) were invalid."
                )
            else:
                # Revoking a group's permissions is blocked while its master is
                # granted, so the hint names the master governing this user.
                master_name = self._master_name(role_group)
                reasons = (
                    f"- {failed_str} permission(s) were already revoked for the user.\n"
                    f"- Provided permission(s) were invalid.\n"
                    f"- If {master_name} is granted, it must be revoked before "
                    f"{failed_str} can be revoked for this user."
                )
            self.reporter.log_info(
                f"Could not {verb_inf} {failed_str} permission(s) "
                f"for user: {user_email}.\nPossible reasons:\n{reasons}"
            )

    @staticmethod
    def _role_team_user_permission_map(
        role: WMUserTypeEnum,
        full_map: dict[int, str],
        groups: dict[str, dict[int, str]] | None,
    ) -> dict[int, str]:
        """Return the subset of team-user permissions available for the role."""
        if not groups:
            return dict(full_map)
        keyword = "contributor" if role == WMUserTypeEnum.Contributor else "admin"
        for group_name, perms in groups.items():
            if keyword in group_name.lower():
                return dict(perms)
        return dict(full_map)

    def _build_cascade(
        self,
        operation: PermissionOperation,
        groups: dict[str, dict[int, str]] | None,
        known_ids: set[int],
    ) -> dict[int, list[int]]:
        # Start from the hardcoded name-based cascades (e.g. Edit -> View
        # custom field values), then derive each group's master cascade from the
        # live permission-groups data: granting a master grants every other
        # permission in its group. Deriving it at runtime avoids hardcoding ids
        # that may not exist for every team (e.g. id 25 can be absent depending
        # on configuration) and keeps non-grantable ids out of the batch.
        base = (
            constants.TEAM_USER_PERMISSION_GRANT_CASCADE
            if operation == "grant"
            else constants.TEAM_USER_PERMISSION_REVOKE_CASCADE
        )
        # The hardcoded cascades name ids by convention, but a team may not have
        # them all. Drop anything this team does not expose, otherwise we would
        # send unknown ids to the backend and fail to name them when reporting.
        cascade = {
            pid: [dep for dep in deps if dep in known_ids]
            for pid, deps in base.items()
            if pid in known_ids
        }
        if operation == "grant" and groups:
            for perms in groups.values():
                master_id = self._group_master(perms)
                if master_id is None:
                    continue
                cascade[master_id] = [
                    pid
                    for pid in perms
                    if pid != master_id and pid not in DEPRECATED_IDS
                ]
        return cascade

    @staticmethod
    def _cascade_team_permission_ids(
        requested: list[int], cascade: dict[int, list[int]]
    ) -> list[int]:
        """Expand requested permission ids with cascade dependents (by id)."""
        expanded = list(requested)
        seen = set(requested)
        for pid in list(requested):
            for dep_id in cascade.get(pid, []):
                if dep_id not in seen:
                    expanded.append(dep_id)
                    seen.add(dep_id)
        return expanded
