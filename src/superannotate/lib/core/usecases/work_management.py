from __future__ import annotations

from typing import Callable
from typing import Literal

import lib.core as constants
from lib.core.entities.work_managament import WMUserTypeEnum
from lib.core.reporter import Reporter
from lib.core.response import Response
from lib.core.serviceproviders import BaseServiceProvider
from lib.core.usecases import BaseReportableUseCase

PermissionOperation = Literal["grant", "revoke"]

# Permission ids used by the cascade rules (see constants).
MANAGE_CONTRIBUTORS_ID = constants.TEAM_USER_PERMISSION_MANAGE_CONTRIBUTORS["id"]


class UpdateUserPermissionUseCase(BaseReportableUseCase):
    """Grant or revoke team-user permissions for a single user.

    Encapsulates the business rules that the work-management permissions API
    does not enforce on its own:

      - "*" resolves only to the permissions allowed for the user's role
        (the backend rejects the whole batch otherwise);
      - permission names are matched case- and apostrophe-insensitively;
      - documented cascades are mirrored client-side (see
        ``constants.TEAM_USER_PERMISSION_GRANT_CASCADE`` /
        ``TEAM_USER_PERMISSION_REVOKE_CASCADE``) because the backend does not
        auto-cascade through the permissions API;
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

        resolved_ids, unresolved_names = self._resolve_permissions(
            team_user.role, name_by_id, groups
        )

        affected_ids: set[int] = set()
        ordered_ids = self._order_team_permission_ids(
            self._cascade_team_permission_ids(resolved_ids, self._operation)
        )
        if ordered_ids:
            affected_ids = self._apply(team_user.id, ordered_ids)

        self._log(ordered_ids, affected_ids, unresolved_names, team_user.email)
        return self._response

    def _groups(self) -> dict[str, dict[int, str]] | None:
        try:
            return self._service_provider.get_team_user_permission_groups()
        except Exception:
            return None

    def _apply(self, contributor_id: int, permission_ids: list[int]) -> set[int]:
        response = self._service_provider.work_management.edit_team_user_permissions(
            contributor_ids=[contributor_id],
            permission_ids=permission_ids,
            operation=self._operation,
        )
        section_key = "add" if self._operation == "grant" else "remove"
        entry = next(
            (
                c
                for c in (response.get(section_key) or [])
                if c.get("id") == contributor_id
            ),
            None,
        )
        if not entry:
            return set()
        return {p["id"] for p in (entry.get("userPermissions") or [])}

    def _resolve_permissions(
        self,
        role: WMUserTypeEnum,
        name_by_id: dict[int, str],
        groups: dict[str, dict[int, str]] | None,
    ) -> tuple[list[int], list[str]]:
        if self._permissions == "*":
            return list(
                self._role_team_user_permission_map(role, name_by_id, groups).keys()
            ), []

        resolved_ids: list[int] = []
        seen_ids: set[int] = set()
        unresolved_names: list[str] = []
        for name in self._permissions:
            pid = self._service_provider.get_team_user_permission_id(name)
            if pid is None:
                unresolved_names.append(name)
            elif pid not in seen_ids:
                resolved_ids.append(pid)
                seen_ids.add(pid)
        return resolved_ids, unresolved_names

    def _log(
        self,
        ordered_ids: list[int],
        affected_ids: set[int],
        unresolved_names: list[str],
        user_email: str,
    ) -> None:
        name_by_id = self._service_provider.get_team_user_permission_id_name_map()
        succeeded_names = [
            name_by_id[pid] for pid in ordered_ids if pid in affected_ids
        ]
        failed_names = [
            name_by_id[pid] for pid in ordered_ids if pid not in affected_ids
        ] + unresolved_names

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
                reasons = (
                    f"- {failed_str} permission(s) were already revoked for the user.\n"
                    f"- Provided permission(s) were invalid.\n"
                    f"- If Manage Contributors' permissions is granted, it must be "
                    f"revoked before {failed_str} can be revoked for this user."
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

    @staticmethod
    def _cascade_team_permission_ids(
        requested: list[int], operation: PermissionOperation
    ) -> list[int]:
        """Expand requested permission ids with cascade dependents (by id)."""
        cascade = (
            constants.TEAM_USER_PERMISSION_GRANT_CASCADE
            if operation == "grant"
            else constants.TEAM_USER_PERMISSION_REVOKE_CASCADE
        )
        expanded = list(requested)
        seen = set(requested)
        for pid in list(requested):
            for dep_id in cascade.get(pid, []):
                if dep_id not in seen:
                    expanded.append(dep_id)
                    seen.add(dep_id)
        return expanded

    @staticmethod
    def _order_team_permission_ids(perm_ids: list[int]) -> list[int]:
        # The master permission auto-grants the other contributor permissions
        # and blocks their revocation while enabled, so process it first.
        if MANAGE_CONTRIBUTORS_ID in perm_ids:
            return [MANAGE_CONTRIBUTORS_ID] + [
                pid for pid in perm_ids if pid != MANAGE_CONTRIBUTORS_ID
            ]
        return list(perm_ids)
