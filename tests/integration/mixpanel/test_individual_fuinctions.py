import os
from unittest import TestCase
from unittest.mock import patch

from src.superannotate import AppException
from src.superannotate import __version__
from src.superannotate import class_distribution
from tests import DATA_SET_PATH


class TestDocumentUrls(TestCase):
    PROJECT_NAME = "TEST_MIX"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PATH = "data_set"

    @property
    def folder_path(self):
        return os.path.join(DATA_SET_PATH, self.TEST_FOLDER_PATH)

    @patch("lib.app.interface.base_interface.Tracker._track")
    def test_get_team_metadata(self, track_method):
        try:
            class_distribution(os.path.join(self.folder_path, "sample_project_vector"), "test")
        except AppException:
            pass
        data = list(track_method.call_args)[0][2]
        assert not data["Success"]
        assert data["Version"] == __version__
        assert data["project_names"] == "test"
