import logging
from collections import defaultdict
from typing import List

import lib.core as constances
from lib.core.conditions import Condition
from lib.core.entities import ContributorEntity
from lib.core.entities import ProjectEntity
from lib.core.entities import TeamEntity
from lib.core.exceptions import AppException
from lib.core.response import Response
from lib.core.serviceproviders import BaseServiceProvider
from lib.core.usecases.base import BaseUseCase
from lib.core.usecases.base import BaseUserBasedUseCase

logger = logging.getLogger("sa")


class UnShareProjectUseCase(BaseUseCase):
    def __init__(
        self,
        service_provider: BaseServiceProvider,
        project: ProjectEntity,
        user_id: str,
    ):
        super().__init__()
        self._service_provider = service_provider
        self._project = project
        self._user_id = user_id

    def execute(self):
        self._response.data = self._service_provider.projects.un_share(
            project=self._project,
            user_id=self._user_id,
        ).data
        logger.info(
            f"Unshared project {self._project.name} from user ID {self._user_id}"
        )
        return self._response


class GetTeamUseCase(BaseUseCase):
    def __init__(self, service_provider: BaseServiceProvider, team_id: int):
        super().__init__()
        self._service_provider = service_provider
        self._team_id = team_id

    def execute(self):
        try:
            response = self._service_provider.get_team(self._team_id)
            if not response.ok:
                raise AppException(response.error)
            self._response.data = response.data
        except Exception:
            raise AppException(
                "Unable to retrieve team data. Please verify your credentials."
            ) from None
        return self._response


class GetCurrentUserUseCase(BaseUseCase):
    def __init__(self, service_provider: BaseServiceProvider, team_id: int):
        super().__init__()
        self._service_provider = service_provider
        self._team_id = team_id

    def execute(self):
        response = self._service_provider.get_user(self._team_id)
        if not response.ok:
            self._response.errors = AppException(
                "Unable to retrieve user data. Please verify your credentials."
            )
        else:
            self._response.data = response.data
        return self._response


class SearchContributorsUseCase(BaseUseCase):
    def __init__(
        self,
        service_provider: BaseServiceProvider,
        team_id: int,
        condition: Condition = None,
    ):
        super().__init__()
        self._service_provider = service_provider
        self._team_id = team_id
        self._condition = condition

    def execute(self):
        res = self._service_provider.search_team_contributors(self._condition)
        self._response.data = res.data
        return self._response


class AddContributorsToProject(BaseUseCase):
    """
    Returns tuple of lists (added, skipped)
    """

    def __init__(
        self,
        team: TeamEntity,
        project: ProjectEntity,
        contributors: List[ContributorEntity],
        service_provider: BaseServiceProvider,
    ):
        super().__init__()
        self._team = team
        self._project = project
        self._contributors = contributors
        self._service_provider = service_provider

    def validate_emails(self):
        email_entity_map = {}
        for c in self._contributors:
            email_entity_map[c.user_id] = c
        len_unique, len_provided = len(email_entity_map), len(self._contributors)
        if len_unique < len_provided:
            logger.info(
                f"Dropping duplicates. Found {len_unique}/{len_provided} unique users."
            )
        self._contributors = email_entity_map.values()

    def execute(self):
        if self.is_valid():
            team_users = set()
            project_users = {user.user_id for user in self._project.users}
            for user in self._team.users:
                if user.user_role > constances.UserRole.ADMIN.value:
                    team_users.add(user.email)
            # collecting pending team users which is not admin
            for user in self._team.pending_invitations:
                if user["user_role"] > constances.UserRole.ADMIN.value:
                    team_users.add(user["email"])
            # collecting pending project users which is not admin
            for user in self._project.unverified_users:
                if user["user_role"] > constances.UserRole.ADMIN.value:
                    project_users.add(user["email"])

            role_email_map = defaultdict(list)
            to_skip = []
            to_add = []
            for contributor in self._contributors:
                role_email_map[contributor.user_role].append(contributor.user_id)
            for role, emails in role_email_map.items():
                _to_add = list(team_users.intersection(emails) - project_users)
                to_add.extend(_to_add)
                to_skip.extend(list(set(emails).difference(_to_add)))
                if _to_add:
                    response = self._service_provider.projects.share(
                        project=self._project,
                        users=[
                            dict(
                                user_id=user_id,
                                user_role=role.value,
                            )
                            for user_id in _to_add
                        ],
                    )
                    if not response.ok:
                        self._response.errors = AppException(response.error)
                        return self._response
                    if response and not response.data.get("invalidUsers"):
                        logger.info(
                            f"Added {len(_to_add)}/{len(emails)} "
                            f"contributors to the project {self._project.name} with the {role.name} role."
                        )

            if to_skip:
                logger.warning(
                    f"Skipped {len(to_skip)}/{len(self._contributors)} "
                    "contributors that are out of the team scope or already have access to the project."
                )
            self._response.data = to_add, to_skip
            return self._response


class InviteContributorsToTeam(BaseUserBasedUseCase):
    """
    Returns tuple of lists (added, skipped)
    """

    def __init__(
        self,
        team: TeamEntity,
        emails: list,
        set_admin: bool,
        service_provider: BaseServiceProvider,
    ):
        super().__init__(emails)
        self._team = team
        self._set_admin = set_admin
        self._service_provider = service_provider

    def execute(self):
        if self.is_valid():
            team_users = {user.email for user in self._team.users}
            # collecting pending team users
            team_users.update(
                {user["email"] for user in self._team.pending_invitations}
            )

            emails = set(self._emails)

            to_skip = list(emails.intersection(team_users))
            to_add = list(emails.difference(to_skip))
            invited, failed = [], to_skip
            if to_skip:
                logger.warning(
                    f"Found {len(to_skip)}/{len(self._emails)} existing members of the team."
                )
            if to_add:
                response = self._service_provider.invite_contributors(
                    team_id=self._team.id,
                    # REMINDER UserRole.VIEWER is the contributor for the teams
                    team_role=constances.UserRole.ADMIN.value
                    if self._set_admin
                    else constances.UserRole.VIEWER.value,
                    emails=to_add,
                )
                invited, failed = (
                    response.data["success"]["emails"],
                    response.data["failed"]["emails"],
                )
                if invited:
                    logger.info(
                        f"Sent team {'admin' if self._set_admin else 'contributor'} invitations"
                        f" to {len(invited)}/{len(self._emails)} users."
                    )
                if failed:
                    to_skip = set(to_skip)
                    to_skip.update(set(failed))
                    logger.info(
                        f"Skipped team {'admin' if self._set_admin else 'contributor'} "
                        f"invitations for {len(failed)}/{len(self._emails)} users."
                    )
            self._response.data = invited, list(to_skip)
            return self._response


class ListSubsetsUseCase(BaseUseCase):
    def __init__(
        self,
        project: ProjectEntity,
        service_provider: BaseServiceProvider,
    ):
        super().__init__()
        self._project = project
        self._service_provider = service_provider

    def validate_arguments(self):
        response = self._service_provider.validate_saqul_query(self._project, "_")
        if not response.ok:
            raise AppException(response.error)

    def execute(self) -> Response:
        if self.is_valid():
            sub_sets_response = self._service_provider.subsets.list(
                project=self._project
            )
            if sub_sets_response.ok:
                self._response.data = sub_sets_response.data
            else:
                self._response.data = []

        return self._response
