"""The test suite's own credential plumbing (tests/env.py, tests/conftest.py)."""

import os
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from tests import conftest
from tests import env

TOKEN = "sa_SOZVLlnbheUITTGb_PXlk2ON5QtqNPWY9bHZJctzlx4EPTkImzncQgRmybgh"


class LoadDotenvTestCase(TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.env_path = Path(self._dir.name) / ".env"
        # The developer's own credentials must not leak into the assertions.
        patcher = patch.dict(os.environ, {}, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        for key in ("SA_TOKEN", "SA_URL", "SA_TEAM_ID"):
            os.environ.pop(key, None)

    def test_values_are_read_into_the_environment(self):
        self.env_path.write_text(
            "# credentials\n"
            f"SA_TOKEN={TOKEN}\n"
            "\n"
            'SA_URL="https://api.devsuperannotate.com"\n'
            "export SA_TEAM_ID = 6085\n"
            "not a pair\n"
        )
        loaded = env.load_dotenv(self.env_path)

        assert loaded == {
            "SA_TOKEN": TOKEN,
            "SA_URL": "https://api.devsuperannotate.com",
            "SA_TEAM_ID": "6085",
        }
        assert os.environ["SA_TOKEN"] == TOKEN
        # Quotes are stripped, comments and malformed lines are ignored.
        assert os.environ["SA_URL"] == "https://api.devsuperannotate.com"
        assert os.environ["SA_TEAM_ID"] == "6085"

    def test_the_environment_wins_over_the_file(self):
        # CI exports the credentials; a leftover .env must not override them.
        self.env_path.write_text(f"SA_TOKEN={TOKEN}\nSA_URL=from-file\n")
        with patch.dict(os.environ, {"SA_URL": "from-environment"}):
            loaded = env.load_dotenv(self.env_path)
            assert os.environ["SA_URL"] == "from-environment"
        assert "SA_URL" not in loaded

    def test_missing_file_is_not_an_error(self):
        # Without a .env the SDK falls back to its own config, as it always did.
        assert env.load_dotenv(Path(self._dir.name) / "absent") == {}

    def test_path_is_overridable(self):
        self.env_path.write_text(f"SA_TOKEN={TOKEN}\n")
        with patch.dict(os.environ, {env.ENV_FILE_ENV: str(self.env_path)}):
            assert env.env_file() == self.env_path
            assert env.load_dotenv() == {"SA_TOKEN": TOKEN}

    def test_dotenv_credentials_reach_the_client(self):
        from superannotate import SAClient

        self.env_path.write_text("SA_TOKEN=token=6085\nSA_URL=https://sa.test\n")
        env.load_dotenv(self.env_path)
        with patch("lib.infrastructure.controller.Controller.get_team"), patch(
            "lib.infrastructure.controller.Controller.get_current_user"
        ):
            client = SAClient()
        assert client.controller.team_id == 6085
        assert client.controller._config.API_URL == "https://sa.test"


class RequiresTokensTestCase(TestCase):
    """The gate in front of the suites that need an extra token from the .env."""

    def _decorate(self, *names):
        @env.requires_tokens(*names)
        class Suite(TestCase):
            pass

        return Suite

    def test_runs_when_every_token_is_there(self):
        with env.environ(**{env.SA_CONTRIBUTOR_TOKEN_ENV: TOKEN}):
            assert env.missing_tokens(env.SA_CONTRIBUTOR_TOKEN_ENV) == []
            suite = self._decorate(env.SA_CONTRIBUTOR_TOKEN_ENV)
        assert getattr(suite, "__unittest_skip__", False) is False

    def test_skips_naming_only_the_missing_ones(self):
        with env.environ(
            **{env.SA_CONTRIBUTOR_TOKEN_ENV: TOKEN, env.OWNER_PERSONAL_TOKEN_ENV: None}
        ):
            names = (env.OWNER_PERSONAL_TOKEN_ENV, env.SA_CONTRIBUTOR_TOKEN_ENV)
            assert env.missing_tokens(*names) == [env.OWNER_PERSONAL_TOKEN_ENV]
            suite = self._decorate(*names)
        assert suite.__unittest_skip__ is True
        assert env.OWNER_PERSONAL_TOKEN_ENV in suite.__unittest_skip_why__
        assert env.SA_CONTRIBUTOR_TOKEN_ENV not in suite.__unittest_skip_why__


def _item(*scopes):
    """A test item carrying a requires_token_scope marker."""
    item = MagicMock()
    item.iter_markers.return_value = [pytest.mark.requires_token_scope(*scopes).mark]
    return item


class TokenScopeMarkerTestCase(TestCase):
    """The marker behind env.requires_organization_token and friends."""

    def test_runs_when_the_scope_matches(self):
        with patch.object(env, "token_scope", return_value=env.ORGANIZATION):
            conftest.pytest_runtest_setup(_item(env.ORGANIZATION))

    def test_skips_when_another_token_type_is_configured(self):
        with patch.object(env, "token_scope", return_value=env.TEAM):
            with pytest.raises(pytest.skip.Exception) as exc:
                conftest.pytest_runtest_setup(_item(env.ORGANIZATION))
        assert "requires a token of scope organization" in str(exc.value)
        assert "the configured one is team" in str(exc.value)

    def test_a_marker_may_accept_several_scopes(self):
        # requires_user_token covers both a personal key and a legacy token.
        for scope in (env.PERSONAL, env.LEGACY):
            with patch.object(env, "token_scope", return_value=scope):
                conftest.pytest_runtest_setup(_item(env.PERSONAL, env.LEGACY))

    def test_declared_markers_carry_the_expected_scopes(self):
        assert env.requires_organization_token.mark.args == (env.ORGANIZATION,)
        assert env.requires_team_token.mark.args == (env.TEAM,)
        assert env.requires_user_token.mark.args == (env.PERSONAL, env.LEGACY)
        assert env.requires_team_scoped_token.mark.args == (
            env.TEAM,
            env.PERSONAL,
            env.LEGACY,
        )

    def test_legacy_token_reports_the_legacy_scope(self):
        client = MagicMock()
        client.controller.token_context.is_legacy = True
        with patch.object(env, "get_client", return_value=client):
            assert env.token_scope() == env.LEGACY

    def test_scope_comes_from_the_token_context(self):
        client = MagicMock()
        client.controller.token_context.is_legacy = False
        client.controller.token_context.scope_type = env.ORGANIZATION
        with patch.object(env, "get_client", return_value=client):
            assert env.token_scope() == env.ORGANIZATION
