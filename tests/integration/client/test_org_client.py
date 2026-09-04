"""What SAORGClient can do: list an organization's teams, and mint a team-scoped
SAClient on demand.

Every test here builds its client from a key named in the .env - SA_ORGANIZATION_TOKEN
for what an org key can do, SA_OWNER_PERSONAL_TOKEN for what it rejects - and is skipped
while that key is unset (see tests/env.py).
"""

import os
from unittest import TestCase

import pytest
from src.superannotate import AppException
from src.superannotate import SAClient
from src.superannotate.lib.core.entities.context import TokenScope
from tests import env


@env.requires_env_vars(env.SA_ORGANIZATION_TOKEN_ENV, env.SA_ORGANIZATION_TEAM_ID_ENV)
class TestOrgClient(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.org_client = env.build_org_client(env.token(env.SA_ORGANIZATION_TOKEN_ENV))
        cls.team_id = int(os.environ[env.SA_ORGANIZATION_TEAM_ID_ENV])

    def test_authenticates_with_no_team(self):
        context = self.org_client.controller.token_context
        assert context.scope == TokenScope.ORGANIZATION
        assert context.team_id is None

    def test_list_teams_contains_the_configured_team(self):
        teams = self.org_client.list_teams()

        assert teams
        matching = next((team for team in teams if team["id"] == self.team_id), None)
        assert matching is not None
        # Only the documented fields - the backend also sends type/user_role/is_default.
        assert matching.keys() == {
            "id",
            "name",
            "description",
            "creator_id",
            "owner_id",
            "owner_type",
        }

    def test_get_team_client_returns_a_working_team_scoped_client(self):
        team_client = self.org_client.get_team_client(self.team_id)

        assert isinstance(team_client, SAClient)
        assert team_client.team_id == self.team_id
        # A real, team-scoped call: proves the returned client actually authenticates
        assert team_client.controller.current_user.email
        team_all_projects = team_client.list_projects()
        assert team_all_projects
        for p in team_all_projects:
            assert p["team_id"] == self.team_id

        self.org_client.list_teams()

    def test_get_team_client_rejects_a_non_integer_team_id(self):
        with self.assertRaisesRegex(AppException, r"Input should be a valid integer"):
            self.org_client.get_team_client("not-an-id")


@env.requires_env_vars(env.OWNER_PERSONAL_TOKEN_ENV)
def test_a_team_bound_token_is_rejected():
    # SAORGClient takes only an organization key: a key bound to one team - personal
    # here, but a team key or a legacy token the same way - cannot act for the org.
    with pytest.raises(AppException, match=r"Invalid credentials provided\."):
        env.build_org_client(env.token(env.OWNER_PERSONAL_TOKEN_ENV))
