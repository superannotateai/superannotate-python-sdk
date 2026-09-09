"""Credentials the test suite runs with, taken from a ``.env`` file.

The suite talks to a real team, and which token it uses changes what the backend allows:
a team-scoped API key acts as the team (there is no user behind it), a personal key acts
as the user it was issued for, and an organization key is not bound to a team at all, so
it only works together with a team id.

Put the credentials in a ``.env`` file at the repository root (override the path with
``SA_TEST_ENV_FILE``)::

    SA_TOKEN=<API key>
    SA_URL=https://api.devsuperannotate.com
    # Only an organization key needs it; any other key carries its own team.
    SA_TEAM_ID=6085

The file is read before the integration modules build their clients, so a plain
``SAClient()`` picks it up. Values already set in the environment win over the file,
which is how CI provides them. With no ``.env`` and no environment the suite falls back
to the SDK's own ``~/.superannotate/config.ini``, as it always did.

Tests that only apply to one kind of token declare it, and are skipped when the ``.env``
holds another kind::

    @env.requires_organization_token
    def test_something_org_only(): ...

A suite may also need a token of its own, beyond the one the run authenticates as - a
project-admin contributor's key, say. Those live under their own variables and gate the
whole module::

    @env.requires_tokens(env.SA_CONTRIBUTOR_TOKEN_ENV)
    class TestSomething(TestCase):
        @classmethod
        def setUpClass(cls):
            cls.client = env.build_client(env.token(env.SA_CONTRIBUTOR_TOKEN_ENV))
"""

import contextlib
import os
import unittest
from functools import lru_cache
from pathlib import Path

#: Overrides the location of the .env file.
ENV_FILE_ENV = "SA_TEST_ENV_FILE"
DEFAULT_ENV_FILE = Path(__file__).parent.parent / ".env"

#: Token scopes, as the backend reports them.
ORGANIZATION = "organization"
TEAM = "team"
PERSONAL = "teamuser"
#: A legacy team-owner token: it carries its team and reports no scope.
LEGACY = "legacy"

#: Tokens the suite can build an extra client with, beyond the ``SA_TOKEN`` it runs as.
#: A suite that needs one declares it (``requires_tokens``) and is skipped without it.
OWNER_PERSONAL_TOKEN_ENV = "SA_OWNER_PERSONAL_TOKEN"
SA_CONTRIBUTOR_TOKEN_ENV = "SA_CONTRIBUTOR_TOKEN"


def env_file() -> Path:
    return Path(os.environ.get(ENV_FILE_ENV) or DEFAULT_ENV_FILE).expanduser()


def load_dotenv(path=None) -> dict:
    """Read a ``.env`` file into the environment and return what it set.

    Only keys that are not already in the environment are set, so an explicitly exported
    variable (CI, or a one-off run) always wins over the file.
    """
    path = Path(path) if path else env_file()
    if not path.is_file():
        return {}
    loaded = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip().removeprefix("export ").strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value
            loaded[key] = value
    return loaded


@lru_cache(maxsize=None)
def get_client():
    """The client the suite runs as, built from the environment (``.env``).

    Cached: building one costs a token-scope round trip to the backend.
    """
    from src.superannotate import SAClient

    load_dotenv()
    return SAClient()


@contextlib.contextmanager
def environ(**values):
    """Temporarily set environment variables; a ``None`` value unsets one."""
    saved = {key: os.environ.get(key) for key in values}
    try:
        for key, value in values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def build_client(token: str, team_id: int | None = None, team_id_via_env: bool = False):
    """An ``SAClient`` for an ad-hoc token, on the backend the ``.env`` names.

    The token reaches the SDK the way the suite's own credentials do - through the
    environment - so ``SA_URL`` from the ``.env`` still applies. Passing it as
    ``SAClient(token=...)`` would not: only the no-argument path reads ``SA_URL``.

    The team is passed as the ``team_id`` argument, or as ``SA_TEAM_ID`` when
    ``team_id_via_env`` is set; both are paths a caller has. It is never inherited from
    the ``.env``, so a client can be built with no team at all.
    """
    from src.superannotate import SAClient

    load_dotenv()
    with environ(
        SA_TOKEN=token,
        SA_TEAM_ID=str(team_id) if team_id is not None and team_id_via_env else None,
    ):
        return SAClient(team_id=None if team_id_via_env else team_id)


def token(name: str) -> str:
    """A token the ``.env`` provides under ``name`` (one of the ``*_TOKEN_ENV``)."""
    load_dotenv()
    return os.environ[name]


def missing_tokens(*names: str) -> list[str]:
    """Which of these tokens the ``.env`` does not provide."""
    load_dotenv()
    return [name for name in names if not os.environ.get(name)]


def requires_tokens(*names: str):
    """Run only when the ``.env`` provides every one of these tokens.

    Unlike ``requires_token_scope``, this asks nothing of the backend: the tokens are
    either in the environment or they are not, so a whole ``TestCase`` can be skipped
    on the spot.
    """
    missing = missing_tokens(*names)
    return unittest.skipIf(
        bool(missing), f"needs {', '.join(missing)} in the .env (see tests/env.py)"
    )


def token_scope() -> str:
    """The scope of the token the suite runs with: one of the constants above."""
    context = get_client().controller.token_context
    return LEGACY if context.is_legacy else context.scope_type


def _requires(*scopes):
    import pytest

    return pytest.mark.requires_token_scope(*scopes)


#: Only runs when the .env token is an organization key.
requires_organization_token = _requires(ORGANIZATION)
#: Only runs when the .env token is a team key (acting as the team, with no user).
requires_team_token = _requires(TEAM)
#: Only runs when the .env token acts as a user: a personal key or a legacy token.
requires_user_token = _requires(PERSONAL, LEGACY)
#: Only runs when the .env token carries its own team - anything but an organization key.
requires_team_scoped_token = _requires(TEAM, PERSONAL, LEGACY)
