import copy
import platform
import tempfile
import threading
from configparser import ConfigParser
from unittest import TestCase
from unittest.mock import patch

import pytest
from src.superannotate import __version__
from src.superannotate import AppException
from src.superannotate import SAClient


class TestMixpanel(TestCase):
    CLIENT = SAClient()
    TEAM_DATA = CLIENT.get_team_metadata()
    BLANK_PAYLOAD = {
        "SDK": True,
        "Team": TEAM_DATA["name"],
        "Team Owner": TEAM_DATA["creator_id"],
        "Version": __version__,
        "Success": True,
        "Python version": platform.python_version(),
        "Python interpreter type": platform.python_implementation(),
    }
    PROJECT_NAME = "TEST_MIX"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PATH = "data_set"

    @classmethod
    def setUpClass(cls) -> None:
        cls.tearDownClass()
        print(cls.PROJECT_NAME)
        cls._project = cls.CLIENT.create_project(
            cls.PROJECT_NAME, cls.PROJECT_DESCRIPTION, cls.PROJECT_TYPE
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._safe_delete_project(cls.PROJECT_NAME)

    @classmethod
    def _safe_delete_project(cls, project_name):
        projects = cls.CLIENT.search_projects(project_name, return_metadata=True)
        for project in projects:
            try:
                cls.CLIENT.delete_project(project)
            except Exception:
                raise

    @property
    def default_payload(self):
        return copy.copy(self.BLANK_PAYLOAD)

    @patch("lib.app.interface.base_interface.Tracker._track")
    def test_init(self, track_method):
        SAClient()
        result = list(track_method.call_args)[0]
        payload = self.default_payload
        payload.update({"token": "False", "config_path": "False"})
        assert result[1] == "__init__"
        assert payload == result[2]

    @patch("lib.app.interface.base_interface.Tracker._track")
    @patch("lib.core.usecases.GetTeamUseCase")
    def test_init_via_token(self, get_team_use_case, track_method):
        SAClient(token="test=3232")
        result = list(track_method.call_args)[0]
        payload = self.default_payload
        payload.update(
            {
                "token": "True",
                "config_path": "False",
                "Team": get_team_use_case().execute().data.name,
                "Team Owner": get_team_use_case().execute().data.creator_id,
            }
        )
        assert result[1] == "__init__"
        assert payload == result[2]

    @patch("lib.app.interface.base_interface.Tracker._track")
    @patch("lib.core.usecases.GetTeamUseCase")
    def test_init_via_config_file(self, get_team_use_case, track_method):
        with tempfile.TemporaryDirectory() as config_dir:
            config_ini_path = f"{config_dir}/config.ini"
            with patch("lib.core.CONFIG_INI_FILE_LOCATION", config_ini_path):
                with open(f"{config_dir}/config.ini", "w") as config_ini:
                    config_parser = ConfigParser()
                    config_parser.optionxform = str
                    config_parser["DEFAULT"] = {"SA_TOKEN": "test=3232"}
                    config_parser.write(config_ini)
                SAClient(config_path=f"{config_dir}/config.ini")
                result = list(track_method.call_args)[0]
                payload = self.default_payload
                payload.update(
                    {
                        "token": "False",
                        "config_path": "True",
                        "Team": get_team_use_case().execute().data.name,
                        "Team Owner": get_team_use_case().execute().data.creator_id,
                    }
                )
                assert result[1] == "__init__"
                assert payload == result[2]

    @patch("lib.app.interface.base_interface.Tracker._track")
    def test_get_team_metadata(self, track_method):
        team = self.CLIENT.get_team_metadata()
        team_owner = team["creator_id"]
        result = list(track_method.call_args)[0]
        payload = self.default_payload
        assert result[0] == team_owner
        assert result[1] == "get_team_metadata"
        assert payload == result[2]

    @patch("lib.app.interface.base_interface.Tracker._track")
    def test_search_team_contributors(self, track_method):
        kwargs = {
            "email": "user@supernnotate.com",
            "first_name": "first_name",
            "last_name": "last_name",
            "return_metadata": False,
        }
        self.CLIENT.search_team_contributors(**kwargs)
        result = list(track_method.call_args)[0]
        payload = self.default_payload
        payload.update(kwargs)
        assert result[1] == "search_team_contributors"
        assert payload == result[2]

    @patch("lib.app.interface.base_interface.Tracker._track")
    def test_search_projects(self, track_method):
        kwargs = {
            "name": self.PROJECT_NAME,
            "include_complete_item_count": True,
            "status": "NotStarted",
            "return_metadata": False,
        }
        self.CLIENT.search_projects(**kwargs)
        result = list(track_method.call_args)[0]
        payload = self.default_payload
        payload.update(kwargs)
        assert result[1] == "search_projects"
        assert payload == result[2]

    @patch("lib.app.interface.base_interface.Tracker._track")
    def test_create_project(self, track_method):
        kwargs = {
            "project_name": self.PROJECT_NAME,
            "project_description": self.PROJECT_DESCRIPTION,
            "project_type": self.PROJECT_TYPE,
            "settings": {"a": 1, "b": 2},
            "classes": None,
            "workflows": None,
            "instructions_link": None,
        }
        try:
            self.CLIENT.create_project(**kwargs)
        except AppException:
            pass
        result = list(track_method.call_args)[0]
        payload = self.default_payload
        payload["Success"] = False
        payload.update(kwargs)
        payload["settings"] = list(kwargs["settings"].keys())
        assert result[1] == "create_project"
        assert payload == result[2]

    @pytest.mark.skip("Need to adjust")
    @patch("lib.app.interface.base_interface.Tracker._track")
    def test_create_project_multi_thread(self, track_method):
        project_1 = self.PROJECT_NAME + "_1"
        project_2 = self.PROJECT_NAME + "_2"
        try:
            kwargs_1 = {
                "project_name": project_1,
                "project_description": self.PROJECT_DESCRIPTION,
                "project_type": self.PROJECT_TYPE,
            }
            kwargs_2 = {
                "project_name": project_2,
                "project_description": self.PROJECT_DESCRIPTION,
                "project_type": self.PROJECT_TYPE,
            }
            thread_1 = threading.Thread(
                target=self.CLIENT.create_project, kwargs=kwargs_1
            )
            thread_2 = threading.Thread(
                target=self.CLIENT.create_project, kwargs=kwargs_2
            )
            thread_1.start()
            thread_2.start()
            thread_1.join()
            thread_2.join()
            r1, r2 = track_method.call_args_list
            r1_pr_name = r1[0][2].pop("project_name")
            r2_pr_name = r2[0][2].pop("project_name")
            assert r1_pr_name == project_1
            assert r2_pr_name == project_2
            assert r1[0][2] == r2[0][2]
        finally:
            self._safe_delete_project(project_1)
            self._safe_delete_project(project_2)
