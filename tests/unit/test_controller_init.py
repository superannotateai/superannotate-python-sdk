import os
from os.path import join
import json
import pkg_resources
import tempfile
import pytest
from unittest import TestCase
from unittest.mock import mock_open
from unittest.mock import patch


from src.superannotate.lib.app.interface.cli_interface import CLIFacade
from src.superannotate.lib.core import CONFIG_FILE_LOCATION
from tests.utils.helpers import catch_prints


try:
    CLI_VERSION = pkg_resources.get_distribution("superannotate").version
except Exception:
    CLI_VERSION = None


class CLITest(TestCase):
    CONFIG_FILE_DATA = '{"main_endpoint": "https://amazonaws.com:3000","token": "c9c55ct=6085","ssl_verify": false}'

    @pytest.mark.skip(reason="Need to adjust")
    @patch('builtins.input')
    def test_init_update(self, input_mock):
        input_mock.side_effect = ["y", "token"]
        with patch('builtins.open', mock_open(read_data=self.CONFIG_FILE_DATA)) as config_file:
            try:
                with catch_prints() as out:
                    cli = CLIFacade()
                    cli.init()
            except SystemExit:
                input_mock.assert_called_with("Input the team SDK token from https://app.superannotate.com/team : ")
                config_file().write.assert_called_once_with(
                    json.dumps(
                        {"main_endpoint": "https://api.devsuperannotate.com", "ssl_verify": False, "token": "token"},
                        indent=4
                    )
                )
                self.assertEqual(out.getvalue().strip(), "Configuration file successfully updated.")

    @pytest.mark.skip(reason="Need to adjust")
    @patch('builtins.input')
    def test_init_create(self, input_mock):
        input_mock.side_effect = ["token"]
        with patch('builtins.open', mock_open(read_data="{}")) as config_file:
            try:
                with catch_prints() as out:
                    cli = CLIFacade()
                    cli.init()
            except SystemExit:
                input_mock.assert_called_with("Input the team SDK token from https://app.superannotate.com/team : ")
                config_file().write.assert_called_once_with(
                    json.dumps(
                        {"token": "token"},
                        indent=4
                    )
                )
                self.assertEqual(out.getvalue().strip(), "Configuration file successfully created.")


class SKDInitTest(TestCase):
    TEST_TOKEN = "toke=123"

    VALID_JSON = {
        "token": "a"*28 + "=1234"
    }
    INVALID_JSON = {
        "token": "a" * 28 + "=1234asd"
    }
    FILE_NAME = "config.json"
    FILE_NAME_2 = "config.json"

    @patch.dict(os.environ, {"SA_TOKEN": TEST_TOKEN})
    def test_env_flow(self):
        import superannotate as sa
        self.assertEqual(sa.get_default_controller()._token, self.TEST_TOKEN)

    def test_init_via_config_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            token_path = f"{temp_dir}/config.json"
            with open(token_path, "w") as temp_config:
                json.dump({"token": self.TEST_TOKEN}, temp_config)
                temp_config.close()
                import src.superannotate as sa
                sa.init(token_path)

    @patch("lib.infrastructure.controller.Controller.retrieve_configs")
    def test_init_default_configs_open(self, retrieve_configs):
        import src.superannotate as sa
        try:
            sa.init()
        except Exception:
            self.assertTrue(retrieve_configs.call_args[0], sa.constances.CONFIG_FILE_LOCATION)

    def test_init(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = join(temp_dir, self.FILE_NAME)
            with open(path, "w") as config:
                json.dump(self.VALID_JSON, config)
            import src.superannotate as sa
            sa.init(path)
            self.assertEqual(sa.get_default_controller().team_id, 1234)
