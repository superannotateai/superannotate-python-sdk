import configparser
import json
from unittest import TestCase
from unittest.mock import Mock
from unittest.mock import mock_open
from unittest.mock import patch

import pytest
from src.superannotate.lib.core import CONFIG_FILE_LOCATION
from src.superannotate.lib.core.entities import ConfigEntity
from src.superannotate.lib.infrastructure.repositories import ConfigRepository


@pytest.mark.skip(reason="Need to adjust")
class TestConfigRepository(TestCase):
    TEST_UUID = "test_uuid"
    FILE_CONTENT = """
    [default]
    test_uuid = test_value
    test_uuid2 = test_value
    """

    def setUp(self) -> None:
        self.repo = ConfigRepository()

    @property
    def config_entity(self):
        return ConfigEntity(uuid="str", value="str")

    @patch(
        "src.superannotate.lib.infrastructure.repositories.ConfigRepository._get_config"
    )
    def test_get_one(self, get_config):
        entity = self.repo.get_one(uuid=self.TEST_UUID)
        get_config.assert_called()
        self.assertIsInstance(entity, ConfigEntity)

    @patch(
        "src.superannotate.lib.infrastructure.repositories.ConfigRepository._get_config"
    )
    def test_get_all(self, get_config):
        config = configparser.ConfigParser()
        config.read_string(self.FILE_CONTENT)
        get_config.return_value = config
        entities = self.repo.get_all()
        get_config.assert_called()
        self.assertEquals(len(entities), 2)

    @patch(
        "src.superannotate.lib.infrastructure.repositories.ConfigRepository._get_config"
    )
    @patch("builtins.open", new_callable=mock_open)
    def test_insert(self, mock_file, get_config):
        config_mock = Mock()
        get_config.return_value = config_mock
        entity = self.repo.insert(self.config_entity)
        get_config.assert_called()
        config_mock.set.assert_called_with(
            "default", self.config_entity.uuid, self.config_entity.value
        )
        mock_file.assert_called_with(CONFIG_FILE_LOCATION, "rw+")
        self.assertIsInstance(entity, ConfigEntity)

    @patch(
        "src.superannotate.lib.infrastructure.repositories.ConfigRepository._get_config"
    )
    @patch("builtins.open", new_callable=mock_open, read_data=json.dumps(FILE_CONTENT))
    def test_update(self, mock_file, get_config):
        self.repo.update(self.config_entity)
        get_config.assert_called()
        mock_file.assert_called_with(CONFIG_FILE_LOCATION, "rw+")

    @patch(
        "src.superannotate.lib.infrastructure.repositories.ConfigRepository._get_config"
    )
    @patch("builtins.open", new_callable=mock_open, read_data=json.dumps(FILE_CONTENT))
    def test_delete(self, mock_file, get_config):
        config_mock = Mock()
        get_config.return_value = config_mock
        self.repo.delete(self.TEST_UUID)
        config_mock.remove_option.assert_called_with("default", self.TEST_UUID)
        mock_file.assert_called_with(CONFIG_FILE_LOCATION, "rw+")
