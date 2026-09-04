import copy
import platform
import tempfile
from configparser import ConfigParser
from unittest import TestCase
from unittest.mock import patch

from src.superannotate import __version__
from src.superannotate import AppException
from src.superannotate import SAClient

sa = SAClient()


class TestMixpanel(TestCase):
    BLANK_PAYLOAD = {
        "Env": "N/A",
        "SDK": True,
        "Team": sa.get_team_metadata()["name"],
        "User Email": sa.controller.current_user.email,
        "Auth Type": sa.controller.token_context.scope.label,
        "Version": __version__,
        "Success": True,
        "Python version": platform.python_version(),
        "Python interpreter type": platform.python_implementation(),
        "Class": "SAClient",
    }
    PROJECT_NAME = "TEST_MIX"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PATH = "data_set"

    @classmethod
    def setUpClass(cls) -> None:
        cls.tearDownClass()
        print(cls.PROJECT_NAME)
        cls._project = sa.create_project(
            cls.PROJECT_NAME, cls.PROJECT_DESCRIPTION, cls.PROJECT_TYPE
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._safe_delete_project(cls.PROJECT_NAME)

    @classmethod
    def _safe_delete_project(cls, project_name):
        projects = sa.list_projects(name=project_name)
        for project in projects:
            try:
                sa.delete_project(project=project["id"])
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
        # Every argument of the signature is tracked: team_id and config are None
        # unless the caller gives them, and a token is reduced to whether it was given.
        payload.update(
            {
                "sa_token": "False",
                "config_path": "False",
                "team_id": None,
                "config": None,
            }
        )
        assert result[1] == "__init__"
        assert payload == result[2]

    @patch("lib.app.interface.base_interface.Tracker._track")
    @patch("lib.core.usecases.GetTeamUseCase")
    @patch("lib.infrastructure.serviceprovider.ServiceProvider.get_user")
    def test_init_via_token(self, get_user, get_team_use_case, track_method):
        get_team_use_case().execute().data.name = "Mocked Team"
        get_user().data.email = "mocked@example.com"
        SAClient(token="test=3232")
        result = list(track_method.call_args)[0]
        payload = self.default_payload
        payload.update(
            {
                "sa_token": "True",
                "config_path": "False",
                "team_id": None,
                "config": None,
                # A legacy "<name>=<team_id>" token, whatever the ambient one is.
                "Auth Type": "SDK Token",
                "Team": "Mocked Team",
                "User Email": "mocked@example.com",
            }
        )
        assert result[1] == "__init__"
        assert payload == result[2]

    @patch("lib.app.interface.base_interface.Tracker._track")
    @patch("lib.core.usecases.GetTeamUseCase")
    @patch("lib.infrastructure.serviceprovider.ServiceProvider.get_user")
    def test_init_via_config_file(self, get_user, get_team_use_case, track_method):
        get_team_use_case().execute().data.name = "Mocked Team"
        get_user().data.email = "mocked@example.com"
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
                        "sa_token": "False",
                        "config_path": "True",
                        "team_id": None,
                        "config": None,
                        "Auth Type": "SDK Token",
                        "Team": "Mocked Team",
                        "User Email": "mocked@example.com",
                    }
                )
                assert result[1] == "__init__"
                assert payload == result[2]

    @patch("lib.app.interface.base_interface.Tracker._track")
    def test_get_team_metadata(self, track_method):
        sa.get_team_metadata()
        team_owner = sa.controller.current_user.email
        result = list(track_method.call_args)[0]
        payload = {**self.default_payload, "include": None}
        assert result[0] == team_owner
        assert result[1] == "get_team_metadata"
        assert payload == result[2]

    @patch("lib.app.interface.base_interface.Tracker._track")
    def test_search_projects(self, track_method):
        kwargs = {
            "name": self.PROJECT_NAME,
            "include_complete_item_count": True,
            "status": "NotStarted",
            "return_metadata": False,
        }
        sa.search_projects(**kwargs)
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
            "workflow": None,
            "instructions_link": None,
            "form": None,
        }
        try:
            sa.create_project(**kwargs)
        except AppException:
            pass
        result = list(track_method.call_args)[0]
        payload = self.default_payload
        payload["Success"] = False
        # Only a failed __init__ carries a reason; this one just marks the failure.
        payload["Failure Reason"] = None
        payload.update(kwargs)
        payload["settings"] = list(kwargs["settings"].keys())
        assert result[1] == "create_project"
        assert payload == result[2]
