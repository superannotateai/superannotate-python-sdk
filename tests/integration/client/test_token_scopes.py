"""What the token in the .env grants, checked against the backend.

Every test here is tied to a token scope, so a run with one kind of key skips the tests
that only make sense for the others. See tests/env.py.
"""

import os

import pytest
from src.superannotate import AppException
from tests import env


def test_token_authenticates(sa_client):
    assert sa_client.controller.team_id
    # Every token resolves the user it acts as, or the creator behind a team key.
    assert sa_client.controller.current_user.email


@env.requires_organization_token
def test_org_token_operates_in_the_configured_team(sa_client):
    context = sa_client.controller.token_context
    assert context.is_organization_key
    assert not context.is_team_key
    assert not context.is_personal_key
    assert sa_client.controller.team_id == int(os.environ["SA_TEAM_ID"])


@env.requires_organization_token
def test_org_token_without_team_id_is_rejected():
    # The team is not part of the key, so there is nothing to fall back on.
    with pytest.raises(
        AppException, match=r'Organization API key requires a "team_id"'
    ):
        env.build_client(os.environ["SA_TOKEN"])


@env.requires_organization_token
def test_org_token_with_a_team_id_argument():
    # The same key, with the team passed as an argument instead of through the .env.
    team_id = int(os.environ["SA_TEAM_ID"])
    client = env.build_client(os.environ["SA_TOKEN"], team_id=team_id)
    assert client.controller.team_id == team_id


@env.requires_organization_token
def test_org_token_with_a_team_id_from_the_environment():
    # SA_TEAM_ID in the .env, which is how the suite itself is configured.
    team_id = int(os.environ["SA_TEAM_ID"])
    client = env.build_client(
        os.environ["SA_TOKEN"], team_id=team_id, team_id_via_env=True
    )
    assert client.controller._config.TEAM_ID == team_id
    assert client.controller.team_id == team_id


@env.requires_team_token
def test_team_token_acts_as_the_team(sa_client):
    context = sa_client.controller.token_context
    assert context.is_team_key
    assert not context.is_personal_key


@env.requires_user_token
def test_personal_token_acts_as_a_user(sa_client):
    context = sa_client.controller.token_context
    assert context.is_personal_key or context.is_legacy


@env.requires_team_scoped_token
def test_team_scoped_token_rejects_a_conflicting_team_id(sa_client):
    # The key names its own team, so a team_id that disagrees is a caller mistake.
    with pytest.raises(AppException, match=r"does not match the team"):
        env.build_client(
            os.environ["SA_TOKEN"], team_id=sa_client.controller.team_id + 1
        )
