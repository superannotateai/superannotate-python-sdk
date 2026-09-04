"""What each kind of token grants, checked against the backend.

A test that only makes sense for one kind of key builds a client from a key of that
kind, named by its own .env variable, and is skipped while that variable is unset (see
tests/env.py). Only the first test uses the ambient SA_TOKEN, whatever kind it is.
"""

import os
from unittest import TestCase

from src.superannotate import AppException
from src.superannotate.lib.core.entities.context import TokenScope
from tests import env


def test_the_suite_token_authenticates(sa_client):
    assert sa_client.controller.team_id
    # Every token resolves the user it acts as, or the creator behind a team key.
    assert sa_client.controller.current_user.email


@env.requires_env_vars(env.SA_ORGANIZATION_TOKEN_ENV, env.SA_ORGANIZATION_TEAM_ID_ENV)
class TestOrganizationToken(TestCase):
    """An organization key is not bound to a team, so the caller names one."""

    @classmethod
    def setUpClass(cls):
        cls.token = env.token(env.SA_ORGANIZATION_TOKEN_ENV)
        cls.team_id = int(os.environ[env.SA_ORGANIZATION_TEAM_ID_ENV])

    def test_team_id_as_an_argument(self):
        client = env.build_client(self.token, team_id=self.team_id)

        assert client.controller.token_context.scope == TokenScope.ORGANIZATION
        assert client.controller.team_id == self.team_id

    def test_team_id_from_the_environment(self):
        client = env.build_client(
            self.token, team_id=self.team_id, team_id_via_env=True
        )

        assert client.controller.config["SA_TEAM_ID"] == self.team_id
        assert client.controller.team_id == self.team_id

    def test_without_a_team_id_is_rejected(self):
        # The team is not part of the key, so there is nothing to fall back on.
        with self.assertRaisesRegex(AppException, r"Invalid credentials provided\."):
            env.build_client(self.token)


@env.requires_env_vars(env.OWNER_PERSONAL_TOKEN_ENV)
class TestPersonalToken(TestCase):
    """A personal key acts as the user it was issued for, and names its own team."""

    @classmethod
    def setUpClass(cls):
        cls.token = env.token(env.OWNER_PERSONAL_TOKEN_ENV)
        cls.client = env.build_client(cls.token)

    def test_acts_as_a_user_of_its_own_team(self):
        context = self.client.controller.token_context

        assert context.scope == TokenScope.TEAM_USER
        assert context.team_id
        assert self.client.controller.current_user.email

    def test_rejects_a_conflicting_team_id(self):
        # The key names its own team, so a team_id that disagrees is a caller mistake.
        with self.assertRaisesRegex(AppException, r"Invalid team id provided\."):
            env.build_client(self.token, team_id=self.client.team_id + 1)
