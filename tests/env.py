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
    # For SAORGClient's own tests - a second, independent key.
    SA_ORGANIZATION_TOKEN=<organization API key>
    SA_ORGANIZATION_TEAM_ID=<a team that key can reach>

The file is read before the integration modules build their clients, so a plain
``SAClient()`` picks it up. Values already set in the environment win over the file,
which is how CI provides them. With no ``.env`` and no environment the suite falls back
to the SDK's own ``~/.superannotate/config.ini``, as it always did.

A test that only makes sense for one kind of token builds a client from a token of that
kind, declared under its own variable, and is skipped while that variable is unset::

    @env.requires_env_vars(env.SA_CONTRIBUTOR_TOKEN_ENV)
    class TestSomething(TestCase):
        @classmethod
        def setUpClass(cls):
            cls.client = env.build_client(env.token(env.SA_CONTRIBUTOR_TOKEN_ENV))
"""

import configparser
import contextlib
import os
import tempfile
import unittest
from functools import lru_cache
from pathlib import Path

#: Overrides the location of the .env file.
ENV_FILE_ENV = "SA_TEST_ENV_FILE"
DEFAULT_ENV_FILE = Path(__file__).parent.parent / ".env"

#: Tokens the suite can build a client with, beyond the ``SA_TOKEN`` it runs as.
#: A suite that needs one declares it (``requires_env_vars``) and is skipped without it.
OWNER_PERSONAL_TOKEN_ENV = "SA_OWNER_PERSONAL_TOKEN"
SA_CONTRIBUTOR_TOKEN_ENV = "SA_CONTRIBUTOR_TOKEN"
#: A key for SAORGClient's own tests, independent of SA_TOKEN's scope, plus a team it
#: can reach.
SA_ORGANIZATION_TOKEN_ENV = "SA_ORGANIZATION_TOKEN"
SA_ORGANIZATION_TEAM_ID_ENV = "SA_ORGANIZATION_TEAM_ID"


def env_file() -> Path:
    return Path(os.environ.get(ENV_FILE_ENV) or DEFAULT_ENV_FILE).expanduser()


def dotenv_values(path=None) -> dict:
    """What a ``.env`` file holds, read straight from the file.

    Unlike ``load_dotenv`` this neither consults nor touches the environment, so it
    still answers when the environment has been scrubbed.
    """
    path = Path(path) if path else env_file()
    if not path.is_file():
        return {}
    values = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip().removeprefix("export ").strip()
        if key:
            values[key] = value.strip().strip("\"'")
    return values


def load_dotenv(path=None) -> dict:
    """Read a ``.env`` file into the environment and return what it set.

    Only keys that are not already in the environment are set, so an explicitly exported
    variable (CI, or a one-off run) always wins over the file.
    """
    loaded = {}
    for key, value in dotenv_values(path).items():
        if key not in os.environ:
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


def _sdk_environ(token: str, team_id: int | None = None) -> dict:
    """The whole environment a client is built in: every variable the SDK reads.

    Every one is set here rather than inherited, so building a client does not depend
    on what the ambient environment happens to hold. Two ways that used to bite:
    a suite that scrubs the environment (``tests/unit/conftest.py``) would silently get
    a client pointed at production, and a stray ``SA_TEAM_ID`` would attach itself to a
    token that never asked for one. The backend comes from the environment first, then
    the ``.env`` file, so an exported override still wins.
    """
    from_file = dotenv_values()
    values = {
        "SA_TOKEN": token,
        "SA_TEAM_ID": str(team_id) if team_id is not None else None,
    }
    # SA_URL only: the SDK reads SA_SSL but can never act on it, since
    # _retrieve_configs_from_env assigns VERIFY_SSL only when it is already True.
    values["SA_URL"] = os.environ.get("SA_URL") or from_file.get("SA_URL")
    return values


def build_client(token: str, team_id: int | None = None, team_id_via_env: bool = False):
    """An ``SAClient`` for an ad-hoc token, on the backend the ``.env`` names.

    The token reaches the SDK the way the suite's own credentials do - through the
    environment - so ``SA_URL`` still applies. Passing it as ``SAClient(token=...)``
    would not: only the no-argument path reads ``SA_URL``.

    The team is passed as the ``team_id`` argument, or as ``SA_TEAM_ID`` when
    ``team_id_via_env`` is set; both are paths a caller has. It is never inherited from
    the ``.env``, so a client can be built with no team at all.
    """
    from src.superannotate import SAClient

    with environ(**_sdk_environ(token, team_id if team_id_via_env else None)):
        return SAClient(team_id=None if team_id_via_env else team_id)


@contextlib.contextmanager
def _config_file(token: str):
    """A throwaway ini config naming the credentials and the backend.

    Given ``config_path``, the SDK reads the file and consults the environment for
    nothing, so a client built from one can neither be perturbed by the ambient
    environment nor leak into it. The backend still comes from the environment first
    and the ``.env`` file second, so an exported override wins as it always did.
    """
    settings = {"SA_TOKEN": token}
    url = os.environ.get("SA_URL") or dotenv_values().get("SA_URL")
    if url:
        settings["SA_URL"] = url
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "config.ini"
        parser = configparser.ConfigParser()
        parser.optionxform = str
        parser["DEFAULT"] = settings
        with path.open("w") as handle:
            parser.write(handle)
        yield str(path)


def build_org_client(token: str):
    """An ``SAORGClient`` for an ad-hoc token, on the backend the ``.env`` names.

    Built from a config file rather than the environment: an organization client is
    bound to no team, so a stray ``SA_TEAM_ID`` must not reach it, and a scrubbed
    ``SA_URL`` must not move it to another backend. Nothing about it is inherited.
    """
    from src.superannotate import SAORGClient

    with _config_file(token) as config_path:
        return SAORGClient(config_path=config_path)


def token(name: str) -> str:
    """A token the ``.env`` provides under ``name`` (one of the ``*_TOKEN_ENV``)."""
    value = os.environ.get(name) or dotenv_values().get(name)
    if not value:
        raise KeyError(name)
    return value


def missing_env_vars(*names: str) -> list[str]:
    """Which of these ``.env`` variables (tokens, team ids, ...) are not provided."""
    from_file = dotenv_values()
    return [name for name in names if not (os.environ.get(name) or from_file.get(name))]


def requires_env_vars(*names: str):
    """Run only when the ``.env`` provides every one of these variables.

    This asks nothing of the backend: a variable is either in the environment or it is
    not, so a test or a whole ``TestCase`` is skipped on the spot.
    """
    missing = missing_env_vars(*names)
    return unittest.skipIf(
        bool(missing), f"needs {', '.join(missing)} in the .env (see tests/env.py)"
    )
