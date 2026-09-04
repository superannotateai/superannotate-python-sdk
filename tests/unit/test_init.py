import json
import os
import tempfile
from configparser import ConfigParser
from copy import deepcopy
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock
from unittest.mock import patch

import superannotate.lib.core as constants
from superannotate import AppException
from superannotate import SAAuthError
from superannotate import SAClient
from superannotate import SAORGClient
from superannotate.lib.app.interface.base_interface import BaseInterfaceFacade
from superannotate.lib.core.entities import OrgTeamEntity
from superannotate.lib.core.entities.context import TokenScope


class ClientInitTestCase(TestCase):
    _token = "token=123"

    def test_init_via_invalid_token(self):
        _token = "123"
        with self.assertRaisesRegex(AppException, r"Invalid token\."):
            SAClient(token=_token)

    @patch("lib.infrastructure.controller.TeamController.get_current_user")
    @patch("lib.core.usecases.GetTeamUseCase")
    def test_init_via_token(self, get_team_use_case, get_current_user):
        sa = SAClient(token=self._token)
        assert get_team_use_case.call_args_list[0].kwargs["team_id"] == int(
            self._token.split("=")[-1]
        )
        assert get_current_user.call_count == 1
        assert sa.controller.config["SA_TOKEN"] == self._token
        assert sa.controller.config["SA_URL"] == constants.BACKEND_URL

    @patch("lib.infrastructure.controller.TeamController.get_current_user")
    @patch("lib.core.usecases.GetTeamUseCase")
    def test_init_via_config_json(self, get_team_use_case, get_current_user):
        with tempfile.TemporaryDirectory() as config_dir:
            config_ini_path = f"{config_dir}/config.ini"
            config_json_path = f"{config_dir}/config.json"
            with patch("lib.core.CONFIG_INI_FILE_LOCATION", config_ini_path), patch(
                "lib.core.CONFIG_JSON_FILE_LOCATION", config_json_path
            ):
                with open(f"{config_dir}/config.json", "w") as config_json:
                    json.dump({"token": self._token}, config_json)
                for kwargs in ({}, {"config_path": f"{config_dir}/config.json"}):
                    sa = SAClient(**kwargs)

                    assert sa.controller.config["SA_TOKEN"] == self._token
                    assert sa.controller.config["SA_URL"] == constants.BACKEND_URL
                    assert get_team_use_case.call_args_list[0].kwargs["team_id"] == int(
                        self._token.split("=")[-1]
                    )
                assert get_current_user.call_count == 2

    def test_init_via_config_json_invalid_json(self):
        with tempfile.TemporaryDirectory() as config_dir:
            config_ini_path = f"{config_dir}/config.ini"
            config_json_path = f"{config_dir}/config.json"
            with patch("lib.core.CONFIG_INI_FILE_LOCATION", config_ini_path), patch(
                "lib.core.CONFIG_JSON_FILE_LOCATION", config_json_path
            ):
                with open(f"{config_dir}/config.json", "w") as config_json:
                    json.dump({"token": "INVALID_TOKEN"}, config_json)
                for kwargs in ({}, {"config_path": f"{config_dir}/config.json"}):
                    with self.assertRaisesRegex(AppException, r"Invalid token\."):
                        SAClient(**kwargs)

    @patch("lib.infrastructure.controller.TeamController.get_current_user")
    @patch("lib.core.usecases.GetTeamUseCase")
    def test_init_via_config_ini(self, get_team_use_case, get_current_user):
        with tempfile.TemporaryDirectory() as config_dir:
            config_ini_path = f"{config_dir}/config.ini"
            config_json_path = f"{config_dir}/config.json"
            with patch("lib.core.CONFIG_INI_FILE_LOCATION", config_ini_path), patch(
                "lib.core.CONFIG_JSON_FILE_LOCATION", config_json_path
            ):
                with open(f"{config_dir}/config.ini", "w") as config_ini:
                    config_parser = ConfigParser()
                    config_parser.optionxform = str
                    config_parser["DEFAULT"] = {
                        "SA_TOKEN": self._token,
                        "LOGGING_LEVEL": "DEBUG",
                    }
                    config_parser.write(config_ini)
                for kwargs in ({}, {"config_path": f"{config_dir}/config.ini"}):
                    sa = SAClient(**kwargs)
                    assert sa.controller.config["SA_TOKEN"] == self._token
                    assert sa.controller.config["LOGGING_LEVEL"] == "DEBUG"
                    assert sa.controller.config["SA_URL"] == constants.BACKEND_URL
                    assert get_team_use_case.call_args_list[0].kwargs["team_id"] == int(
                        self._token.split("=")[-1]
                    )
                assert get_current_user.call_count == 2

    @patch("lib.infrastructure.controller.TeamController.get_current_user")
    @patch("lib.core.usecases.GetTeamUseCase")
    def test_init_via_config_relative_filepath(
        self, get_team_use_case, get_current_user
    ):
        with tempfile.TemporaryDirectory(dir=Path("~").expanduser()) as config_dir:
            config_ini_path = f"{config_dir}/config.ini"
            config_json_path = f"{config_dir}/config.json"
            with patch("lib.core.CONFIG_INI_FILE_LOCATION", config_ini_path), patch(
                "lib.core.CONFIG_JSON_FILE_LOCATION", config_json_path
            ):
                with open(f"{config_dir}/config.ini", "w") as config_ini:
                    config_parser = ConfigParser()
                    config_parser.optionxform = str
                    config_parser["DEFAULT"] = {
                        "SA_TOKEN": self._token,
                        "LOGGING_LEVEL": "DEBUG",
                    }
                    config_parser.write(config_ini)
                for kwargs in (
                    {},
                    {"config_path": f"~/{Path(config_dir).name}/config.ini"},
                ):
                    sa = SAClient(**kwargs)
                    assert sa.controller.config["SA_TOKEN"] == self._token
                    assert sa.controller.config["LOGGING_LEVEL"] == "DEBUG"
                    assert sa.controller.config["SA_URL"] == constants.BACKEND_URL
                    assert get_team_use_case.call_args_list[0].kwargs["team_id"] == int(
                        self._token.split("=")[-1]
                    )
                assert get_current_user.call_count == 2

    @patch("lib.infrastructure.controller.TeamController.get_current_user")
    @patch("lib.infrastructure.controller.TeamController.get_team")
    @patch.dict(os.environ, {"SA_URL": "SOME_URL", "SA_TOKEN": "SOME_TOKEN=123"})
    def test_init_env(self, get_team, get_current_user):
        sa = SAClient()
        assert sa.controller.config["SA_TOKEN"] == "SOME_TOKEN=123"
        assert sa.controller.config["SA_URL"] == "SOME_URL"
        assert get_team.call_count == 1
        assert get_current_user.call_count == 1

    @patch.dict(os.environ, {"SA_URL": "SOME_URL", "SA_TOKEN": "SOME_TOKEN"})
    def test_init_env_invalid_token(self):
        with self.assertRaisesRegex(AppException, r"Invalid token\."):
            SAClient()

    def test_init_via_config_ini_invalid_token(self):
        with tempfile.TemporaryDirectory() as config_dir:
            config_ini_path = f"{config_dir}/config.ini"
            config_json_path = f"{config_dir}/config.json"
            with patch("lib.core.CONFIG_INI_FILE_LOCATION", config_ini_path), patch(
                "lib.core.CONFIG_JSON_FILE_LOCATION", config_json_path
            ):
                with open(f"{config_dir}/config.ini", "w") as config_ini:
                    config_parser = ConfigParser()
                    config_parser.optionxform = str
                    config_parser["DEFAULT"] = {
                        "SA_TOKEN": "INVALID_TOKEN",
                        "LOGGING_LEVEL": "DEBUG",
                    }
                    config_parser.write(config_ini)

                for kwargs in ({}, {"config_path": f"{config_dir}/config.ini"}):
                    with self.assertRaisesRegex(AppException, r"Invalid token\."):
                        SAClient(**kwargs)

    def test_invalid_config_path(self):
        _path = "something"
        with self.assertRaisesRegex(
            AppException, f"SuperAnnotate config file {_path} not found."
        ):
            SAClient(config_path=_path)


def _mock_response(payload: dict, ok: bool = True, status_code: int = 200):
    response = MagicMock()
    response.ok = ok
    response.status_code = status_code
    response.text = json.dumps(payload)
    response.json.return_value = payload
    return response


TEAM_TOKEN_RESPONSE = {
    "user": None,
    "token": {
        "id": 1794,
        "scope_id": "6085",
        "status": "ACTIVE",
        "scope": {"team_id": 6085},
        "created_by": "vaghinak@superannotate.com",
        "name": "test 12",
        "public_id": "UBDC6K2KiSrshky1",
        "scope_type": "team",
    },
}

TEAM_USER_TOKEN_RESPONSE = {
    "user": {
        "id": "vaghinak@superannotate.com",
        "first_name": "Vaghinak",
        "last_name": "Basentsyan",
        "email": "vaghinak@superannotate.com",
    },
    "token": {
        "id": 1795,
        "scope_id": "vaghinak@superannotate.com",
        "parent_scope_id": "6085",
        "scope": {"user_id": "vaghinak@superannotate.com", "team_id": 6085},
        "created_by": "vaghinak@superannotate.com",
        "scope_type": "teamuser",
        "status": "ACTIVE",
    },
}

ORGANIZATION_TOKEN_RESPONSE = {
    "user": None,
    "token": {
        "id": 1796,
        "scope_id": "org-1",
        "scope": {"organization_id": "org-1"},
        "created_by": "vaghinak@superannotate.com",
        "scope_type": "organization",
        "status": "ACTIVE",
    },
}


@patch("lib.infrastructure.controller.TeamController.get_team")
@patch("lib.infrastructure.services.auth.requests.post")
class ApiKeyInitTestCase(TestCase):
    _token = "sa_SOZVLlnbheUITTGb_PXlk2ON5QtqNPWY9bHZJctzlx4EPTkImzncQgRmybgh"

    def test_init_via_team_token(self, post, get_team):
        post.return_value = _mock_response(TEAM_TOKEN_RESPONSE)
        sa = SAClient(token=self._token)

        assert sa.controller.team_id == 6085
        # A team-scoped token has no user behind it, so it falls back to its creator.
        assert sa.controller.current_user.email == "vaghinak@superannotate.com"
        # The team id comes from the token, but telemetry reports the team *name*,
        # so init resolves the team once and caches it.
        assert get_team.call_count == 1

        client = sa.controller.service_provider.client
        assert client.team_id == 6085
        assert client.auth_type == "api_key"
        assert client.default_headers["authtype"] == "api_key"
        assert client.default_headers["Authorization"] == self._token

        # The scope is kept: a team key acts as the team, so it is not allowed to
        # perform user-level operations (updating a team admin's permissions).
        context = sa.controller.token_context
        assert context.scope == TokenScope.TEAM

    def test_token_context_request(self, post, get_team):
        post.return_value = _mock_response(TEAM_TOKEN_RESPONSE)
        SAClient(token=self._token)

        assert post.call_count == 1
        url = post.call_args.args[0]
        assert url.endswith("/users/me")
        assert post.call_args.kwargs["json"] == {}
        headers = post.call_args.kwargs["headers"]
        assert headers["authtype"] == "api_key"
        assert headers["Authorization"] == self._token

    def test_team_is_fetched_once(self, post, get_team):
        # The token carries the team id, so the team itself is fetched only when
        # something needs its data - the telemetry team name on init, here - and
        # every later reader is served from the cache.
        post.return_value = _mock_response(TEAM_TOKEN_RESPONSE)
        get_team.return_value.data = MagicMock(owner_id="org-1")
        sa = SAClient(token=self._token)

        assert get_team.call_count == 1
        assert sa.controller.org_id == "org-1"
        assert sa.controller.team.owner_id == "org-1"
        assert get_team.call_count == 1

    def test_init_via_team_user_token(self, post, get_team):
        post.return_value = _mock_response(TEAM_USER_TOKEN_RESPONSE)
        sa = SAClient(token=self._token)

        assert sa.controller.team_id == 6085
        assert sa.controller.current_user.email == "vaghinak@superannotate.com"
        assert sa.controller.current_user.first_name == "Vaghinak"

        # A personal key acts as its user, so it may do what that user may do.
        context = sa.controller.token_context
        assert context.scope == TokenScope.TEAM_USER

    def test_nested_service_clients_share_team_context(self, post, get_team):
        post.return_value = _mock_response(TEAM_TOKEN_RESPONSE)
        sa = SAClient(token=self._token)

        for service in (
            sa.controller.service_provider.work_management,
            sa.controller.service_provider.item_service,
        ):
            assert service.client.team_id == 6085
            assert service.client.auth_type == "api_key"

    def test_organization_api_key_without_team_id_rejected(self, post, get_team):
        # An organization key carries no team, so it cannot resolve one on its own.
        post.return_value = _mock_response(ORGANIZATION_TOKEN_RESPONSE)
        with self.assertRaisesRegex(AppException, r"Invalid credentials provided\."):
            SAClient(token=self._token)

    def test_organization_api_key_with_team_id(self, post, get_team):
        # The team is not part of the key, so the caller names the team to operate in.
        post.return_value = _mock_response(ORGANIZATION_TOKEN_RESPONSE)
        sa = SAClient(token=self._token, team_id=6085)

        assert sa.controller.team_id == 6085
        context = sa.controller.token_context
        assert context.scope == TokenScope.ORGANIZATION
        # A team-less key has no user behind it either, so it falls back to its creator.
        assert sa.controller.current_user.email == "vaghinak@superannotate.com"

        client = sa.controller.service_provider.client
        assert client.team_id == 6085
        assert client.auth_type == "api_key"

    def test_team_id_matching_the_token_accepted(self, post, get_team):
        post.return_value = _mock_response(TEAM_TOKEN_RESPONSE)
        sa = SAClient(token=self._token, team_id=6085)
        assert sa.controller.team_id == 6085

    def test_team_id_mismatching_the_token_rejected(self, post, get_team):
        # A team key names its own team; a conflicting team_id is a caller mistake.
        post.return_value = _mock_response(TEAM_TOKEN_RESPONSE)
        with self.assertRaisesRegex(AppException, r"Invalid team id provided\."):
            SAClient(token=self._token, team_id=42)

    def test_unknown_scope_type_rejected(self, post, get_team):
        response = deepcopy(TEAM_TOKEN_RESPONSE)
        response["token"]["scope_type"] = "something-new"
        post.return_value = _mock_response(response)
        with self.assertRaisesRegex(AppException, r"Invalid team id provided\."):
            SAClient(token=self._token)

    def test_team_scope_without_team_id_rejected(self, post, get_team):
        # A malformed team-scoped response must not resolve to a team-less client.
        response = deepcopy(TEAM_TOKEN_RESPONSE)
        response["token"]["scope"] = {}
        post.return_value = _mock_response(response)
        with self.assertRaisesRegex(AppException, r"Invalid team id provided\."):
            SAClient(token=self._token)

    def test_authentication_failure(self, post, get_team):
        post.return_value = _mock_response({}, ok=False, status_code=401)
        with self.assertRaisesRegex(AppException, r"Invalid credentials provided\."):
            SAClient(token=self._token)


@patch("lib.infrastructure.controller.TeamController.get_team")
@patch("lib.infrastructure.services.auth.requests.post")
class TeamIdFromConfigTestCase(TestCase):
    """The team an organization key operates in may come from any config source."""

    _token = "sa_SOZVLlnbheUITTGb_PXlk2ON5QtqNPWY9bHZJctzlx4EPTkImzncQgRmybgh"

    def setUp(self):
        self._config_dir = tempfile.TemporaryDirectory()
        config_dir = self._config_dir.name
        self._ini_path = f"{config_dir}/config.ini"
        self._json_path = f"{config_dir}/config.json"
        patches = (
            patch("lib.core.CONFIG_INI_FILE_LOCATION", self._ini_path),
            patch("lib.core.CONFIG_JSON_FILE_LOCATION", self._json_path),
        )
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self._config_dir.cleanup)

    def _write_ini(self, **values):
        config_parser = ConfigParser()
        config_parser.optionxform = str
        config_parser["DEFAULT"] = {k: str(v) for k, v in values.items()}
        with open(self._ini_path, "w") as config_ini:
            config_parser.write(config_ini)

    def test_team_id_from_config_ini(self, post, get_team):
        post.return_value = _mock_response(ORGANIZATION_TOKEN_RESPONSE)
        self._write_ini(SA_TOKEN=self._token, SA_TEAM_ID=6085)
        # Both the default location and an explicit path read the same file.
        for kwargs in ({}, {"config_path": self._ini_path}):
            sa = SAClient(**kwargs)
            assert sa.controller.config["SA_TEAM_ID"] == 6085
            assert sa.controller.team_id == 6085

    def test_team_id_from_config_ini_by_field_name(self, post, get_team):
        # The ini keys are read as-is, so the internal field name works as well.
        post.return_value = _mock_response(ORGANIZATION_TOKEN_RESPONSE)
        self._write_ini(SA_TOKEN=self._token, TEAM_ID=6085)
        assert SAClient().controller.team_id == 6085

    def test_org_token_in_config_ini_without_team_id_rejected(self, post, get_team):
        post.return_value = _mock_response(ORGANIZATION_TOKEN_RESPONSE)
        self._write_ini(SA_TOKEN=self._token)
        with self.assertRaisesRegex(AppException, r"Invalid credentials provided\."):
            SAClient()

    def test_team_id_from_config_json(self, post, get_team):
        post.return_value = _mock_response(ORGANIZATION_TOKEN_RESPONSE)
        with open(self._json_path, "w") as config_json:
            json.dump({"token": self._token, "team_id": 6085}, config_json)
        for kwargs in ({}, {"config_path": self._json_path}):
            assert SAClient(**kwargs).controller.team_id == 6085

    def test_team_id_from_env(self, post, get_team):
        post.return_value = _mock_response(ORGANIZATION_TOKEN_RESPONSE)
        with patch.dict(os.environ, {"SA_TOKEN": self._token, "SA_TEAM_ID": "6085"}):
            assert SAClient().controller.team_id == 6085

    def test_explicit_team_id_overrides_config_ini(self, post, get_team):
        post.return_value = _mock_response(ORGANIZATION_TOKEN_RESPONSE)
        self._write_ini(SA_TOKEN=self._token, SA_TEAM_ID=6085)
        assert SAClient(team_id=1).controller.team_id == 1


class LegacyTokenTestCase(TestCase):
    @patch("lib.infrastructure.controller.TeamController.get_current_user")
    @patch("lib.infrastructure.controller.TeamController.get_team")
    @patch("lib.infrastructure.services.auth.requests.post")
    def test_legacy_token_resolves_offline(self, post, get_team, get_current_user):
        sa = SAClient(token="token=123")

        assert post.call_count == 0
        assert sa.controller.team_id == 123
        assert sa.controller.service_provider.client.auth_type == "sdk"
        # The backend reports no scope for a legacy token; the SDK names it LEGACY.
        # It acts as the team owner, so it may update team admin permissions.
        context = sa.controller.token_context
        assert context.scope == TokenScope.LEGACY

    @patch("lib.infrastructure.controller.TeamController.get_current_user")
    @patch("lib.infrastructure.controller.TeamController.get_team")
    def test_legacy_token_team_id_mismatch_raises(self, get_team, get_current_user):
        with self.assertRaisesRegex(AppException, r"Invalid team id provided\."):
            SAClient(token="token=123", team_id=42)


@patch("lib.infrastructure.services.auth.requests.post")
class OrgClientInitTestCase(TestCase):
    """SAORGClient authenticates outside any team, so it accepts only an org key."""

    _token = "sa_SOZVLlnbheUITTGb_PXlk2ON5QtqNPWY9bHZJctzlx4EPTkImzncQgRmybgh"

    def test_init_via_organization_token(self, post):
        post.return_value = _mock_response(ORGANIZATION_TOKEN_RESPONSE)
        org = SAORGClient(token=self._token)

        context = org.controller.token_context
        assert context.scope == TokenScope.ORGANIZATION
        # No team to scope to, so no team header and no team query param either.
        assert context.team_id is None
        client = org.controller.service_provider.client
        assert client.team_id is None
        assert client.default_query_params == {}
        assert "x-sa-entity-context" not in client.default_headers
        # A team-less key has no user behind it, so it falls back to its creator.
        assert org.controller.current_user.email == "vaghinak@superannotate.com"

    def test_organization_client_is_not_team_bound(self, post):
        # SA_TEAM_ID in the environment does not make an org client team-scoped.
        post.return_value = _mock_response(ORGANIZATION_TOKEN_RESPONSE)
        with patch.dict(os.environ, {"SA_TEAM_ID": "6085"}):
            org = SAORGClient(token=self._token)

        assert org.controller.token_context.team_id is None
        # Nothing team-level is reachable through an organization client.
        assert not hasattr(org.controller, "team_id")
        assert not hasattr(org.controller, "projects")
        # ... and telemetry gets no team name to report, rather than an error.
        assert org.controller.team_name is None

    def test_team_token_rejected(self, post):
        post.return_value = _mock_response(TEAM_TOKEN_RESPONSE)
        with self.assertRaisesRegex(AppException, r"Invalid credentials provided\."):
            SAORGClient(token=self._token)

    def test_personal_token_rejected(self, post):
        post.return_value = _mock_response(TEAM_USER_TOKEN_RESPONSE)
        with self.assertRaisesRegex(AppException, r"Invalid credentials provided\."):
            SAORGClient(token=self._token)

    def test_legacy_token_rejected(self, post):
        # A legacy token resolves offline and is bound to its own team.
        with self.assertRaisesRegex(AppException, r"Invalid credentials provided\."):
            SAORGClient(token="token=123")
        assert post.call_count == 0

    def test_unknown_scope_rejected(self, post):
        response = deepcopy(ORGANIZATION_TOKEN_RESPONSE)
        response["token"]["scope_type"] = "something-new"
        post.return_value = _mock_response(response)
        with self.assertRaisesRegex(AppException, r"Invalid credentials provided\."):
            SAORGClient(token=self._token)

    def test_organization_token_with_no_creator_is_rejected(self, post):
        # There is no team to look a user up in, so a key with no creator behind it
        # has no user at all - and no team-scoped fallback to find one.
        response = deepcopy(ORGANIZATION_TOKEN_RESPONSE)
        response["token"]["created_by"] = None
        post.return_value = _mock_response(response)
        with self.assertRaisesRegex(AppException, r"Invalid credentials provided\."):
            SAORGClient(token=self._token)

    @patch("lib.infrastructure.serviceprovider.ServiceProvider.list_teams")
    def test_list_teams_returns_only_the_documented_fields(self, list_teams, post):
        post.return_value = _mock_response(ORGANIZATION_TOKEN_RESPONSE)
        list_teams.return_value = MagicMock(
            ok=True,
            data=[
                OrgTeamEntity(
                    id=6085,
                    name="Team A",
                    description="",
                    creator_id="a@b.com",
                    owner_id="org-1",
                    owner_type="organization",
                )
            ],
        )

        teams = SAORGClient(token=self._token).list_teams()

        assert [team["id"] for team in teams] == [6085]
        assert teams[0].keys() == {
            "id",
            "name",
            "description",
            "creator_id",
            "owner_id",
            "owner_type",
        }

    def _org_config_ini(self, directory, **settings):
        path = f"{directory}/config.ini"
        parser = ConfigParser()
        parser.optionxform = str
        parser["DEFAULT"] = {"SA_TOKEN": self._token, **settings}
        with open(path, "w") as handle:
            parser.write(handle)
        return path

    @patch("lib.infrastructure.controller.TeamController.get_team")
    def test_get_team_client_keeps_the_configuration_it_was_built_with(
        self, get_team, post
    ):
        # An organization client is configured like any other - a config file, or
        # SA_URL. The team client it hands back has to run on that same configuration:
        # rebuilding one from the token alone reverts to the defaults, which means
        # production.
        post.return_value = _mock_response(ORGANIZATION_TOKEN_RESPONSE)
        with tempfile.TemporaryDirectory() as directory:
            config_path = self._org_config_ini(
                directory, SA_URL="https://sa.test", ANNOTATION_CHUNK_SIZE="100"
            )
            org = SAORGClient(config_path=config_path)
            assert org.controller.config["SA_URL"] == "https://sa.test"

            team_client = org.get_team_client(6085)

        assert team_client.team_id == 6085
        assert team_client.controller.config["SA_URL"] == "https://sa.test"
        assert team_client.controller.config["ANNOTATION_CHUNK_SIZE"] == 100
        # ... and every request it makes goes to that backend, not just the config.
        assert (
            team_client.controller.service_provider.client.api_url == "https://sa.test"
        )

    def test_config_round_trips_through_the_public_constructor(self, post):
        # controller.config is exactly the dict SAClient(config=...) takes, so a client
        # can be rebuilt from another one - which is all get_team_client does.
        post.return_value = _mock_response(ORGANIZATION_TOKEN_RESPONSE)
        with tempfile.TemporaryDirectory() as directory:
            config_path = self._org_config_ini(
                directory, SA_URL="https://sa.test", ITEM_CHUNK_SIZE="250"
            )
            org = SAORGClient(config_path=config_path)

            config = org.controller.config
            rebuilt = SAORGClient(config=config)

        assert config["SA_URL"] == "https://sa.test"
        assert config["ITEM_CHUNK_SIZE"] == 250
        assert config["SA_TOKEN"] == self._token
        # Every key it hands out is one the constructor accepts, and nothing is lost.
        assert rebuilt.controller.config == config

    def test_config_is_a_copy(self, post):
        # It is dumped per access, so a caller cannot reconfigure a live client through
        # the dict it was handed.
        post.return_value = _mock_response(ORGANIZATION_TOKEN_RESPONSE)
        org = SAORGClient(token=self._token)

        org.controller.config["SA_URL"] = "https://mutated.test"

        assert org.controller.config["SA_URL"] == constants.BACKEND_URL

    @patch("lib.infrastructure.controller.TeamController.get_team")
    def test_get_team_client_is_scoped_to_the_requested_team(self, get_team, post):
        post.return_value = _mock_response(ORGANIZATION_TOKEN_RESPONSE)
        org = SAORGClient(token=self._token)

        team_client = org.get_team_client(6085)

        assert isinstance(team_client, SAClient)
        assert team_client.team_id == 6085
        # The same organization key and user, now scoping every request to one team.
        context = team_client.controller.token_context
        assert context.token == org.controller.token_context.token
        assert context.scope == TokenScope.ORGANIZATION
        assert context.user == org.controller.token_context.user
        assert context.team_id == 6085
        client = team_client.controller.service_provider.client
        assert client.default_query_params == {"team_id": 6085}
        # The organization client it came from keeps its own, team-less session.
        assert org.controller.token_context.team_id is None

    @patch("lib.infrastructure.controller.TeamController.get_team")
    def test_get_team_client_resolves_the_token_a_second_time(self, get_team, post):
        # The price of going through the public constructor: it is handed a config, so
        # it resolves the token from scratch and asks the backend about it again. The
        # alternative was constructing the client around __init__, which a user-facing
        # class should not have to expose.
        post.return_value = _mock_response(ORGANIZATION_TOKEN_RESPONSE)
        org = SAORGClient(token=self._token)
        resolved_once = post.call_count

        org.get_team_client(6085)

        assert post.call_count == resolved_once + 1

    @patch("lib.infrastructure.serviceprovider.ServiceProvider.get_team")
    def test_get_team_client_does_not_check_the_team(self, get_team, post):
        # An organization key is authorised across the organization, so construction
        # accepts whatever team it is given, even one the backend refuses. The failure
        # is reported on the first team-scoped call instead - with GetTeamUseCase's
        # one message, which is what the integration test asserts against a real
        # backend.
        post.return_value = _mock_response(ORGANIZATION_TOKEN_RESPONSE)
        get_team.return_value = _mock_response(
            {"error": "team not found"}, ok=False, status_code=404
        )
        org = SAORGClient(token=self._token)

        client = org.get_team_client(999_999_999)

        assert client.team_id == 999_999_999
        with self.assertRaisesRegex(AppException, r"Unable to retrieve team data"):
            client.get_team_metadata()


@patch("lib.infrastructure.services.auth.requests.post")
class AuthErrorTestCase(TestCase):
    """Credential failures are SAAuthError; everything else stays an AppException.

    A caller can act on the difference - reauthenticate rather than retry - and
    telemetry recognises an auth failure by type instead of by matching the message.
    """

    _token = "sa_SOZVLlnbheUITTGb_PXlk2ON5QtqNPWY9bHZJctzlx4EPTkImzncQgRmybgh"

    def test_a_malformed_token_is_an_auth_error(self, post):
        with self.assertRaisesRegex(SAAuthError, r"Invalid token\."):
            SAClient(token="nope")
        # Rejected on shape alone, without asking the backend.
        assert post.call_count == 0

    def test_a_team_id_the_token_disagrees_with_is_an_auth_error(self, post):
        post.return_value = _mock_response(TEAM_TOKEN_RESPONSE)
        with self.assertRaisesRegex(SAAuthError, r"Invalid team id provided\."):
            SAClient(token=self._token, team_id=42)

    def test_the_wrong_kind_of_key_is_an_auth_error(self, post):
        post.return_value = _mock_response(TEAM_TOKEN_RESPONSE)
        with self.assertRaisesRegex(SAAuthError, r"Invalid credentials provided\."):
            SAORGClient(token=self._token)

    def test_missing_credentials_are_an_auth_error(self, post):
        with patch.object(
            BaseInterfaceFacade, "_retrieve_configs_from_env", return_value=None
        ), patch("lib.core.CONFIG_INI_FILE_LOCATION", "/nonexistent.ini"), patch(
            "lib.core.CONFIG_JSON_FILE_LOCATION", "/nonexistent.json"
        ):
            with self.assertRaisesRegex(SAAuthError, r"Credentials not found"):
                SAClient()

    def test_an_auth_error_is_still_an_app_exception(self, post):
        # Callers catching AppException today keep working.
        with self.assertRaises(AppException):
            SAClient(token="nope")

    def test_a_bad_argument_is_not_an_auth_error(self, post):
        post.return_value = _mock_response(TEAM_TOKEN_RESPONSE)
        with self.assertRaises(AppException) as caught:
            SAClient(token=self._token, team_id="not-an-int")
        assert not isinstance(caught.exception, SAAuthError)


@patch("lib.infrastructure.controller.TeamController.get_team")
@patch("lib.infrastructure.services.auth.requests.post")
class InlineConfigTestCase(TestCase):
    """``config=`` configures a client on creation, instead of through a file."""

    _token = "sa_SOZVLlnbheUITTGb_PXlk2ON5QtqNPWY9bHZJctzlx4EPTkImzncQgRmybgh"

    def test_config_alone_is_enough_to_build_a_client(self, post, get_team):
        post.return_value = _mock_response(TEAM_TOKEN_RESPONSE)

        sa = SAClient(
            config={
                "SA_TOKEN": self._token,
                "SA_URL": "https://sa.test",
                "MAX_THREAD_COUNT": 8,
            }
        )

        assert sa.controller.config["SA_TOKEN"] == self._token
        assert sa.controller.config["SA_URL"] == "https://sa.test"
        assert sa.controller.config["MAX_THREAD_COUNT"] == 8

    def test_config_applies_on_top_of_a_token_argument(self, post, get_team):
        post.return_value = _mock_response(TEAM_TOKEN_RESPONSE)

        sa = SAClient(token=self._token, config={"SA_URL": "https://sa.test"})

        assert sa.controller.config["SA_TOKEN"] == self._token
        assert sa.controller.config["SA_URL"] == "https://sa.test"

    def test_config_applies_on_top_of_the_environment(self, post, get_team):
        post.return_value = _mock_response(TEAM_TOKEN_RESPONSE)
        with patch.dict(
            os.environ, {"SA_TOKEN": self._token, "SA_URL": "https://from-env.test"}
        ):
            sa = SAClient(config={"SA_URL": "https://sa.test"})

        assert sa.controller.config["SA_URL"] == "https://sa.test"

    def test_an_explicit_argument_wins_over_the_same_key_in_config(
        self, post, get_team
    ):
        post.return_value = _mock_response(ORGANIZATION_TOKEN_RESPONSE)

        sa = SAClient(team_id=6085, config={"SA_TOKEN": self._token, "SA_TEAM_ID": 42})

        assert sa.controller.team_id == 6085

    def test_an_unrecognised_key_is_rejected(self, post, get_team):
        # ConfigEntity ignores what it does not know, so an unchecked typo would be
        # dropped in silence - and a mistyped SA_TOKEN would send the client off to
        # authenticate as whatever the environment happens to hold.
        post.return_value = _mock_response(TEAM_TOKEN_RESPONSE)

        with self.assertRaisesRegex(AppException, r"Unknown configuration: SA_URLL"):
            SAClient(token=self._token, config={"SA_URLL": "https://typo.test"})

    def test_config_is_keyword_only(self, post, get_team):
        post.return_value = _mock_response(TEAM_TOKEN_RESPONSE)

        with self.assertRaises(AppException):
            SAClient(self._token, None, None, {"SA_URL": "https://sa.test"})
