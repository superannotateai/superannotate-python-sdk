"""The test suite's own credential plumbing (tests/env.py)."""

import json
import os
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock
from unittest.mock import patch

import superannotate  # noqa: F401
from tests import env

# Imported for its side effect as much as its contents: importing the package puts the
# SDK's internal `lib` package on sys.path, which the patch targets below address.

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
        with patch("lib.infrastructure.controller.TeamController.get_team"), patch(
            "lib.infrastructure.controller.TeamController.get_current_user"
        ):
            client = SAClient()
        assert client.controller.team_id == 6085
        assert client.controller.config["SA_URL"] == "https://sa.test"


class RequiresEnvVarsTestCase(TestCase):
    """The gate in front of the suites that need extra variables from the .env."""

    def _decorate(self, *names):
        @env.requires_env_vars(*names)
        class Suite(TestCase):
            pass

        return Suite

    def test_runs_when_every_token_is_there(self):
        with env.environ(**{env.SA_CONTRIBUTOR_TOKEN_ENV: TOKEN}):
            assert env.missing_env_vars(env.SA_CONTRIBUTOR_TOKEN_ENV) == []
            suite = self._decorate(env.SA_CONTRIBUTOR_TOKEN_ENV)
        assert getattr(suite, "__unittest_skip__", False) is False

    def test_skips_naming_only_the_missing_ones(self):
        with env.environ(
            **{env.SA_CONTRIBUTOR_TOKEN_ENV: TOKEN, env.OWNER_PERSONAL_TOKEN_ENV: None}
        ):
            names = (env.OWNER_PERSONAL_TOKEN_ENV, env.SA_CONTRIBUTOR_TOKEN_ENV)
            assert env.missing_env_vars(*names) == [env.OWNER_PERSONAL_TOKEN_ENV]
            suite = self._decorate(*names)
        assert suite.__unittest_skip__ is True
        assert env.OWNER_PERSONAL_TOKEN_ENV in suite.__unittest_skip_why__
        assert env.SA_CONTRIBUTOR_TOKEN_ENV not in suite.__unittest_skip_why__


class _BuilderFixture(TestCase):
    """A .env naming a backend, plus canned token-scope responses.

    Shared by the two builders' cases. The unit suite scrubs the credential variables
    (tests/unit/conftest.py), so a builder that inherited any of them would behave
    differently here than in an integration run - and would quietly point a client at
    production.
    """

    TEAM_TOKEN = {
        "user": None,
        "token": {
            "scope": {"team_id": 6085},
            "scope_type": "team",
            "created_by": "a@b.com",
            "status": "ACTIVE",
        },
    }
    ORG_TOKEN = {
        "user": None,
        "token": {
            "scope": {"organization_id": "org-1"},
            "scope_type": "organization",
            "created_by": "a@b.com",
            "status": "ACTIVE",
        },
    }
    API_KEY = "sa_SOZVLlnbheUITTGb_PXlk2ON5QtqNPWY9bHZJctzlx4EPTkImzncQgRmybgh"

    def setUp(self):
        self.env_path = Path(tempfile.mkdtemp()) / ".env"
        self.env_path.write_text("SA_URL=https://sa.test\n")
        patcher = patch.dict(os.environ, {env.ENV_FILE_ENV: str(self.env_path)})
        patcher.start()
        self.addCleanup(patcher.stop)

    @staticmethod
    def _response(payload):
        response = MagicMock()
        response.ok = True
        response.status_code = 200
        response.text = json.dumps(payload)
        response.json.return_value = payload
        return response

    def _respond_with(self, payload):
        return patch(
            "lib.infrastructure.services.auth.requests.post",
            return_value=self._response(payload),
        )


class BuildClientTestCase(_BuilderFixture):
    """env.build_client sets every variable the SDK reads, inheriting none."""

    def test_the_backend_comes_from_the_dotenv_even_when_the_environment_is_scrubbed(
        self,
    ):
        with self._respond_with(self.TEAM_TOKEN):
            client = env.build_client(self.API_KEY)

        assert client.controller.config["SA_URL"] == "https://sa.test"

    def test_an_exported_url_still_wins_over_the_file(self):
        with patch.dict(os.environ, {"SA_URL": "https://exported.test"}):
            with self._respond_with(self.TEAM_TOKEN):
                client = env.build_client(self.API_KEY)

        assert client.controller.config["SA_URL"] == "https://exported.test"

    def test_an_ambient_team_id_does_not_attach_itself_to_the_token(self):
        # A team key names its own team; an inherited SA_TEAM_ID that disagreed would
        # be rejected as a conflicting team id.
        with patch.dict(os.environ, {"SA_TEAM_ID": "42"}):
            with self._respond_with(self.TEAM_TOKEN):
                client = env.build_client(self.API_KEY)

        assert client.controller.team_id == 6085

    def test_nothing_is_left_behind_in_the_environment(self):
        # It used to call load_dotenv, which writes to os.environ for good.
        with self._respond_with(self.TEAM_TOKEN):
            env.build_client(self.API_KEY)

        assert "SA_TOKEN" not in os.environ
        assert "SA_URL" not in os.environ


class BuildOrgClientTestCase(_BuilderFixture):
    """env.build_org_client goes through a config file, not the environment.

    An organization client is bound to no team, so a stray SA_TEAM_ID must not reach
    it; and config_path makes the SDK ignore the environment altogether, so there is
    nothing to perturb it and nothing to put back.
    """

    def test_it_is_built_with_no_team_whatever_the_environment_holds(self):
        with patch.dict(os.environ, {"SA_TEAM_ID": "6085"}):
            with self._respond_with(self.ORG_TOKEN):
                client = env.build_org_client(self.API_KEY)

        assert client.controller.token_context.team_id is None
        assert client.controller.config["SA_URL"] == "https://sa.test"

    def test_the_environment_is_untouched_while_it_is_built(self):
        # The point of the config file: nothing is written to the environment, not even
        # for the duration of the call. Observed from inside the auth request, which
        # happens mid-construction - checking afterwards proves nothing, because a
        # save-and-restore approach also leaves the environment as it found it.
        seen = {}

        def record(*args, **kwargs):
            seen["SA_TOKEN"] = os.environ.get("SA_TOKEN")
            seen["SA_TEAM_ID"] = os.environ.get("SA_TEAM_ID")
            return self._response(self.ORG_TOKEN)

        with patch.dict(os.environ, {"SA_TEAM_ID": "6085"}), patch(
            "lib.infrastructure.services.auth.requests.post", side_effect=record
        ):
            client = env.build_org_client(self.API_KEY)

        assert client.controller.token_context.token == self.API_KEY
        # The token never entered the environment, and the ambient team id was left
        # exactly as it was rather than being cleared and put back.
        assert seen["SA_TOKEN"] is None
        assert seen["SA_TEAM_ID"] == "6085"


class MissingEnvVarsTestCase(TestCase):
    """The gate reads the file directly, so it answers with the environment scrubbed."""

    def setUp(self):
        self.env_path = Path(tempfile.mkdtemp()) / ".env"
        patcher = patch.dict(os.environ, {env.ENV_FILE_ENV: str(self.env_path)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_variable_only_the_file_provides_counts_as_present(self):
        self.env_path.write_text(f"{env.SA_CONTRIBUTOR_TOKEN_ENV}={TOKEN}\n")

        assert env.missing_env_vars(env.SA_CONTRIBUTOR_TOKEN_ENV) == []
        assert env.token(env.SA_CONTRIBUTOR_TOKEN_ENV) == TOKEN
        # ... and reading it did not put it in the environment.
        assert env.SA_CONTRIBUTOR_TOKEN_ENV not in os.environ

    def test_a_variable_nobody_provides_is_reported_missing(self):
        self.env_path.write_text("")

        assert env.missing_env_vars(env.SA_CONTRIBUTOR_TOKEN_ENV) == [
            env.SA_CONTRIBUTOR_TOKEN_ENV
        ]
