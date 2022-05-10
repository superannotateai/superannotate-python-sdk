from unittest import TestCase

from src.superannotate import SAClient
sa = SAClient()


class BaseTestCase(TestCase):
    PROJECT_1 = "project_1"
    PROJECT_2 = "project_2"

    def setUp(self, *args, **kwargs):
        self.tearDown()

    def tearDown(self) -> None:
        try:
            for project_name in (self.PROJECT_1, self.PROJECT_2):
                projects = sa.search_projects(project_name, return_metadata=True)
                for project in projects:
                    try:
                        sa.delete_project(project)
                    except Exception:
                        pass
        except Exception as e:
            print(str(e))


class TestSearchProjectVector(BaseTestCase):
    PROJECT_1 = "project_1TestSearchProject"
    PROJECT_2 = "project_2TestSearchProject"
    PROJECT_TYPE = "Vector"

    @property
    def projects(self):
        return self.PROJECT_2, self.PROJECT_1

    def test_create_project_without_settings(self):
        project = sa.create_project(self.PROJECT_1, "desc", self.PROJECT_TYPE)
        assert project["name"] == self.PROJECT_1

    def test_create_project_with_settings(self):
        sa.create_project(
            self.PROJECT_1, "desc", self.PROJECT_TYPE,
            [{"attribute": "ImageQuality", "value": "original"}]
        )
        project = sa.get_project_metadata(self.PROJECT_1, include_settings=True)
        for setting in project["settings"]:
            if setting["attribute"] == "ImageQuality":
                assert setting["value"] == "original"


class TestSearchProjectVideo(BaseTestCase):
    PROJECT_1 = "project_1TestSearchProjectVideo"
    PROJECT_2 = "project_2TestSearchProjectVideo"
    PROJECT_TYPE = "Video"

    @property
    def projects(self):
        return self.PROJECT_2, self.PROJECT_1

    def test_create_project_without_settings(self):
        project = sa.create_project(self.PROJECT_1, "desc", self.PROJECT_TYPE)
        assert project["name"] == self.PROJECT_1

    def test_create_project_with_settings(self):
        sa.create_project(
            self.PROJECT_1, "desc", self.PROJECT_TYPE,
            [{"attribute": "FrameRate", "value": 1}]
        )
        project = sa.get_project_metadata(self.PROJECT_1, include_settings=True)
        for setting in project["settings"]:
            if setting["attribute"] == "FrameRate":
                assert setting["value"] == 1