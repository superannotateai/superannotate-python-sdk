import json
import os
import tempfile
from configparser import ConfigParser
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import superannotate.lib.core as constants
from superannotate import AppException
from superannotate import SAClient


class ClientInitTestCase(TestCase):
    _token = "token=123"

    def test_init_via_invalid_token(self):
        _token = "123"
        with self.assertRaisesRegexp(AppException, r"(\s+)token(\s+)Invalid token."):
            SAClient(token=_token)

    @patch("lib.core.usecases.GetTeamUseCase")
    def test_init_via_token(self, get_team_use_case):
        sa = SAClient(token=self._token)
        assert get_team_use_case.call_args_list[0].kwargs["team_id"] == int(
            self._token.split("=")[-1]
        )
        assert sa.controller._config.API_TOKEN == self._token
        assert sa.controller._config.API_URL == constants.BACKEND_URL

    @patch("lib.core.usecases.GetTeamUseCase")
    def test_init_via_config_json(self, get_team_use_case):
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
                    with self.assertRaisesRegexp(
                        AppException, r"(\s+)token(\s+)Invalid token."
                    ):
                        SAClient(**kwargs)

    @patch("lib.core.usecases.GetTeamUseCase")
    def test_init_via_config_ini(self, get_team_use_case):
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

    @patch("lib.core.usecases.GetTeamUseCase")
    def test_init_via_config_relative_filepath(self, get_team_use_case):
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

    @patch("lib.core.usecases.GetTeamUseCase")
    @patch.dict(os.environ, {"SA_URL": "SOME_URL", "SA_TOKEN": "SOME_TOKEN=123"})
    def test_init_env(self, get_team_use_case):
        sa = SAClient()
        assert sa.controller._config.API_TOKEN == "SOME_TOKEN=123"
        assert sa.controller._config.API_URL == "SOME_URL"
        assert get_team_use_case.call_args_list[0].kwargs["team_id"] == 123

    @patch.dict(os.environ, {"SA_URL": "SOME_URL", "SA_TOKEN": "SOME_TOKEN"})
    def test_init_env_invalid_token(self):
        with self.assertRaisesRegexp(AppException, r"(\s+)SA_TOKEN(\s+)Invalid token."):
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
                    with self.assertRaisesRegexp(
                        AppException, r"(\s+)SA_TOKEN(\s+)Invalid token."
                    ):
                        SAClient(**kwargs)

    def test_invalid_config_path(self):
        _path = "something"
        with self.assertRaisesRegexp(
            AppException, f"SuperAnnotate config file {_path} not found."
        ):
            SAClient(config_path=_path)
