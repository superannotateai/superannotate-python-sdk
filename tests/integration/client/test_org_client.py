"""What SAORGClient can do: list an organization's teams, and mint a team-scoped
SAClient on demand.

The "positive" tests need their own key (SA_ORGANIZATION_TOKEN, see tests/env.py) and
gate the whole class, same as the project-admin contributor suite. The rejection tests
instead gate on the ambient SA_TOKEN's own scope, like test_token_scopes.py.
"""

import os
from unittest import TestCase

import pytest
from src.superannotate import AppException
from src.superannotate import SAClient
from src.superannotate import SAORGClient
from tests import env


@env.requires_env_vars(env.SA_ORGANIZATION_TOKEN_ENV, env.SA_ORGANIZATION_TEAM_ID_ENV)
class TestOrgClient(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.org_client = env.build_org_client(env.token(env.SA_ORGANIZATION_TOKEN_ENV))
        cls.team_id = int(os.environ[env.SA_ORGANIZATION_TEAM_ID_ENV])

    def test_authenticates_with_no_team(self):
        context = self.org_client.controller.token_context
        assert context.is_organization_key
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

    def test_get_team_client_reports_an_inaccessible_team_as_not_found(self):
        # Nonexistent or another org's team - reported the same way either way.
        with self.assertRaisesRegex(AppException, r"Team not found"):
            self.org_client.get_team_client(999_999_999)


@env.requires_team_token
def test_team_token_is_rejected():
    # Uses the suite's own ambient SA_TOKEN - no second client needed.
    with pytest.raises(AppException, match=r"Invalid credentials provided\."):
        SAORGClient()


@env.requires_user_token
def test_personal_or_legacy_token_is_rejected():
    with pytest.raises(AppException, match=r"Invalid credentials provided\."):
        SAORGClient()
