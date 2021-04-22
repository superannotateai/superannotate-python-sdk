import json

from unittest import TestCase
from unittest.mock import mock_open
from unittest.mock import patch

from src.lib.infrastructure.repositories import ConfigRepository
from src.lib.core.entities import ConfigEntity
from src.lib.core import CONFIG_FILE_LOCATION


class TestConfigRepository(TestCase):
    TEST_UUID = "test_uuid"
    FILE_CONTENT = {
        "test_uuid": "test_value",
        "test_uuid2": "test_value"
    }

    def setUp(self) -> None:
        self.repo = ConfigRepository()

    @property
    def config_entity(self):
        return ConfigEntity(uuid="str",  value="str")

    @patch("builtins.open", new_callable=mock_open, read_data=json.dumps(FILE_CONTENT))
    def test_get_one(self, mock_file):
        entity = self.repo.get_one(uuid=self.TEST_UUID)
        mock_file.assert_called_with(CONFIG_FILE_LOCATION, 'r')
        self.assertIsInstance(entity, ConfigEntity)

    @patch("builtins.open", new_callable=mock_open, read_data=json.dumps(FILE_CONTENT))
    def test_get_all(self, mock_file):
        entities = self.repo.get_all()
        mock_file.assert_called_with(CONFIG_FILE_LOCATION, 'r')
        self.assertEquals(len(entities), len(self.FILE_CONTENT))

    @patch("builtins.open", new_callable=mock_open, read_data=json.dumps(FILE_CONTENT))
    def test_insert(self, mock_file):
        entity = self.repo.insert(self.config_entity)
        mock_file.assert_called_with(CONFIG_FILE_LOCATION, 'rw+')
        self.assertIsInstance(entity, ConfigEntity)

    @patch("builtins.open", new_callable=mock_open, read_data=json.dumps(FILE_CONTENT))
    def test_update(self, mock_file):
        self.repo.update(self.config_entity)
        mock_file.assert_called_with(CONFIG_FILE_LOCATION, 'rw+')

    @patch("builtins.open", new_callable=mock_open, read_data=json.dumps(FILE_CONTENT))
    def test_delete(self, mock_file):
        self.repo.delete(self.TEST_UUID)
        mock_file.assert_called_with(CONFIG_FILE_LOCATION, 'rw+')
