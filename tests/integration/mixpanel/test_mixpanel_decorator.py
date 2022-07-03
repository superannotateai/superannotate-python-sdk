import copy
import threading
from unittest import TestCase
from unittest.mock import patch

from src.superannotate import SAClient
from src.superannotate import AppException
from src.superannotate import __version__


class TestMixpanel(TestCase):
    CLIENT = SAClient()
    TEAM_DATA = CLIENT.get_team_metadata()
    BLANK_PAYLOAD = {
        "SDK": True,
        "Team": TEAM_DATA["name"],
        "Team Owner": TEAM_DATA["creator_id"],
        "Version": __version__,
        "Success": True
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
    def test_get_team_metadata(self, track_method):
        team = self.CLIENT.get_team_metadata()
        team_owner = team["creator_id"]
        result = list(track_method.call_args)[0]
        payload = self.default_payload
        assert result[0] == team_owner
        assert result[1] == "get_team_metadata"
        assert payload == list(track_method.call_args)[0][2]

    @patch("lib.app.interface.base_interface.Tracker._track")
    def test_search_team_contributors(self, track_method):
        kwargs = {
            "email": "user@supernnotate.com",
            "first_name": "first_name",
            "last_name": "last_name",
            "return_metadata": False}
        self.CLIENT.search_team_contributors(**kwargs)
        result = list(track_method.call_args)[0]
        payload = self.default_payload
        payload.update(kwargs)
        assert result[1] == "search_team_contributors"
        assert payload == list(track_method.call_args)[0][2]

    @patch("lib.app.interface.base_interface.Tracker._track")
    def test_search_projects(self, track_method):
        kwargs = {
            "name": self.PROJECT_NAME,
            "include_complete_image_count": True,
            "status": "NotStarted",
            "return_metadata": False}
        self.CLIENT.search_projects(**kwargs)
        result = list(track_method.call_args)[0]
        payload = self.default_payload
        payload.update(kwargs)
        assert result[1] == "search_projects"
        assert payload == list(track_method.call_args)[0][2]

    @patch("lib.app.interface.base_interface.Tracker._track")
    def test_create_project(self, track_method):
        kwargs = {
            "project_name": self.PROJECT_NAME,
            "project_description": self.PROJECT_DESCRIPTION,
            "project_type": self.PROJECT_TYPE,
            "settings": {"a": 1, "b": 2}
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
        assert payload == list(track_method.call_args)[0][2]

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
            thread_1 = threading.Thread(target=self.CLIENT.create_project, kwargs=kwargs_1)
            thread_2 = threading.Thread(target=self.CLIENT.create_project, kwargs=kwargs_2)
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