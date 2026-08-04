import json
import os
import tempfile
from configparser import ConfigParser
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock
from unittest.mock import patch

import superannotate.lib.core as constants
from superannotate import AppException
from superannotate import SAClient


class ClientInitTestCase(TestCase):
    _token = "token=123"

    def test_init_via_invalid_token(self):
        _token = "123"
        with self.assertRaisesRegex(AppException, r"Invalid token\."):
            SAClient(token=_token)

    @patch("lib.infrastructure.controller.Controller.get_current_user")
    @patch("lib.core.usecases.GetTeamUseCase")
    def test_init_via_token(self, get_team_use_case, get_current_user):
        sa = SAClient(token=self._token)
        assert get_team_use_case.call_args_list[0].kwargs["team_id"] == int(
            self._token.split("=")[-1]
        )
        assert get_current_user.call_count == 1
        assert sa.controller._config.API_TOKEN == self._token
        assert sa.controller._config.API_URL == constants.BACKEND_URL

    @patch("lib.infrastructure.controller.Controller.get_current_user")
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

                    assert sa.controller._config.API_TOKEN == self._token
                    assert sa.controller._config.API_URL == constants.BACKEND_URL
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

    @patch("lib.infrastructure.controller.Controller.get_current_user")
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
                    assert sa.controller._config.API_TOKEN == self._token
                    assert sa.controller._config.LOGGING_LEVEL == "DEBUG"
                    assert sa.controller._config.API_URL == constants.BACKEND_URL
                    assert get_team_use_case.call_args_list[0].kwargs["team_id"] == int(
                        self._token.split("=")[-1]
                    )
                assert get_current_user.call_count == 2

    @patch("lib.infrastructure.controller.Controller.get_current_user")
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
                    assert sa.controller._config.API_TOKEN == self._token
                    assert sa.controller._config.LOGGING_LEVEL == "DEBUG"
                    assert sa.controller._config.API_URL == constants.BACKEND_URL
                    assert get_team_use_case.call_args_list[0].kwargs["team_id"] == int(
                        self._token.split("=")[-1]
                    )
                assert get_current_user.call_count == 2

    @patch("lib.infrastructure.controller.Controller.get_current_user")
    @patch("lib.infrastructure.controller.Controller.get_team")
    @patch.dict(os.environ, {"SA_URL": "SOME_URL", "SA_TOKEN": "SOME_TOKEN=123"})
    def test_init_env(self, get_team, get_current_user):
        sa = SAClient()
        assert sa.controller._config.API_TOKEN == "SOME_TOKEN=123"
        assert sa.controller._config.API_URL == "SOME_URL"
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


@patch("lib.infrastructure.controller.Controller.get_team")
@patch("lib.infrastructure.services.auth.requests.post")
class ApiKeyInitTestCase(TestCase):
    _token = "sa_SOZVLlnbheUITTGb_PXlk2ON5QtqNPWY9bHZJctzlx4EPTkImzncQgRmybgh"

    def test_init_via_team_token(self, post, get_team):
        post.return_value = _mock_response(TEAM_TOKEN_RESPONSE)
        sa = SAClient(token=self._token)

        assert sa.controller.team_id == 6085
        # A team-scoped token has no user behind it, so it falls back to its creator.
        assert sa.controller.current_user.email == "vaghinak@superannotate.com"
        # The token already carries the team, so no team lookup on init.
        assert get_team.call_count == 0

        client = sa.controller.service_provider.client
        assert client.team_id == 6085
        assert client.auth_type == "api_key"
        assert client.default_headers["authtype"] == "api_key"
        assert client.default_headers["Authorization"] == self._token

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

    def test_team_is_fetched_lazily(self, post, get_team):
        post.return_value = _mock_response(TEAM_TOKEN_RESPONSE)
        get_team.return_value.data = MagicMock(owner_id="org-1")
        sa = SAClient(token=self._token)

        assert get_team.call_count == 0
        assert sa.controller.org_id == "org-1"
        assert get_team.call_count == 1
        # Cached afterwards.
        assert sa.controller.team.owner_id == "org-1"
        assert get_team.call_count == 1

    def test_init_via_team_user_token(self, post, get_team):
        post.return_value = _mock_response(TEAM_USER_TOKEN_RESPONSE)
        sa = SAClient(token=self._token)

        assert sa.controller.team_id == 6085
        assert sa.controller.current_user.email == "vaghinak@superannotate.com"
        assert sa.controller.current_user.first_name == "Vaghinak"

    def test_nested_service_clients_share_team_context(self, post, get_team):
        post.return_value = _mock_response(TEAM_TOKEN_RESPONSE)
        sa = SAClient(token=self._token)

        for service in (
            sa.controller.service_provider.work_management,
            sa.controller.service_provider.item_service,
        ):
            assert service.client.team_id == 6085
            assert service.client.auth_type == "api_key"

    def test_init_via_organization_token_without_team(self, post, get_team):
        post.return_value = _mock_response(ORGANIZATION_TOKEN_RESPONSE)
        with self.assertRaisesRegex(AppException, r"not scoped to a team"):
            SAClient(token=self._token)

    def test_init_via_organization_token_with_team_id(self, post, get_team):
        post.return_value = _mock_response(ORGANIZATION_TOKEN_RESPONSE)
        sa = SAClient(token=self._token, team_id=6085)

        assert sa.controller.team_id == 6085
        assert sa.controller.service_provider.client.team_id == 6085
        assert sa.controller.current_user.email == "vaghinak@superannotate.com"

    def test_init_via_organization_token_with_team_id_from_env(self, post, get_team):
        post.return_value = _mock_response(ORGANIZATION_TOKEN_RESPONSE)
        with patch.dict(os.environ, {"SA_TOKEN": self._token, "SA_TEAM_ID": "6085"}):
            sa = SAClient()

        assert sa.controller.team_id == 6085

    def test_init_via_organization_token_with_team_id_from_ini(self, post, get_team):
        post.return_value = _mock_response(ORGANIZATION_TOKEN_RESPONSE)
        with tempfile.TemporaryDirectory() as config_dir:
            config_path = f"{config_dir}/config.ini"
            with open(config_path, "w") as config_ini:
                config_parser = ConfigParser()
                config_parser.optionxform = str
                config_parser["DEFAULT"] = {
                    "SA_TOKEN": self._token,
                    "SA_TEAM_ID": "6085",
                }
                config_parser.write(config_ini)
            sa = SAClient(config_path=config_path)

        assert sa.controller.team_id == 6085

    def test_explicit_team_id_wins_over_config(self, post, get_team):
        post.return_value = _mock_response(ORGANIZATION_TOKEN_RESPONSE)
        with patch.dict(os.environ, {"SA_TOKEN": self._token, "SA_TEAM_ID": "1"}):
            sa = SAClient(team_id=6085)

        assert sa.controller.team_id == 6085

    def test_team_id_mismatch_raises(self, post, get_team):
        post.return_value = _mock_response(TEAM_TOKEN_RESPONSE)
        with self.assertRaisesRegex(AppException, r"does not match the team"):
            SAClient(token=self._token, team_id=42)

    def test_authentication_failure(self, post, get_team):
        post.return_value = _mock_response({}, ok=False, status_code=401)
        with self.assertRaisesRegex(AppException, r"Unable to authenticate"):
            SAClient(token=self._token)


class LegacyTokenTeamIdTestCase(TestCase):
    @patch("lib.infrastructure.controller.Controller.get_current_user")
    @patch("lib.infrastructure.controller.Controller.get_team")
    @patch("lib.infrastructure.services.auth.requests.post")
    def test_legacy_token_resolves_offline(self, post, get_team, get_current_user):
        sa = SAClient(token="token=123")

        assert post.call_count == 0
        assert sa.controller.team_id == 123
        assert sa.controller.service_provider.client.auth_type == "sdk"

    @patch("lib.infrastructure.controller.Controller.get_current_user")
    @patch("lib.infrastructure.controller.Controller.get_team")
    def test_legacy_token_team_id_mismatch_raises(self, get_team, get_current_user):
        with self.assertRaisesRegex(AppException, r"does not match the team"):
            SAClient(token="token=123", team_id=42)
