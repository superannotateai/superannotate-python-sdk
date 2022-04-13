import src.superannotate as sa
from unittest import TestCase


class TestSettings(TestCase):
    PROJECT_NAME = "TestSettings"
    SECOND_PROJECT_NAME = "SecondTestSettings"
    PROJECT_DESCRIPTION = "TestSettings"
    PROJECT_TYPE = "Vector"

    def setUp(self) -> None:
        self.tearDown()

    def tearDown(self) -> None:
        try:
            projects = sa.search_projects(self.PROJECT_NAME, return_metadata=True)
            projects.extend(sa.search_projects(self.SECOND_PROJECT_NAME, return_metadata=True))
            for project in projects:
                try:
                    sa.delete_project(project)
                except Exception:
                    pass
        except Exception as e:
            print(str(e))

    def test_create_project_with_empty_settings(self):
        sa.create_project(
            self.PROJECT_NAME,
            self.PROJECT_DESCRIPTION,
            self.PROJECT_TYPE,
            []
        )
        settings = sa.get_project_settings(self.PROJECT_NAME)
        for setting in settings:
            if setting["attribute"] == "ImageQuality":
                assert setting["value"] == "compressed"
                break
        else:
            raise Exception("Test failed")

    def test_create_project_with_settings(self):
        sa.create_project(
            self.PROJECT_NAME,
            self.PROJECT_DESCRIPTION,
            self.PROJECT_TYPE,
            [{"attribute": "ImageQuality", "value": "original"}])

        settings = sa.get_project_settings(self.PROJECT_NAME)
        for setting in settings:
            if setting["attribute"] == "ImageQuality":
                assert setting["value"] == "original"
                break
        else:
            raise Exception("Test failed")

    def test_create_from_metadata(self):
        sa.create_project(
            self.PROJECT_NAME,
            self.PROJECT_DESCRIPTION,
            self.PROJECT_TYPE,
            [{"attribute": "ImageQuality", "value": "original"}]
        )
        project_metadata = sa.get_project_metadata(self.PROJECT_NAME, include_settings=True)
        project_metadata["name"] = self.SECOND_PROJECT_NAME
        sa.create_project_from_metadata(project_metadata)
        settings = sa.get_project_settings(self.SECOND_PROJECT_NAME)
        for setting in settings:
            if setting["attribute"] == "ImageQuality":
                assert setting["value"] == "original"
                break
        else:
            raise Exception("Test failed")

    def test_clone_project(self):
        sa.create_project(
            self.PROJECT_NAME,
            self.PROJECT_DESCRIPTION,
            self.PROJECT_TYPE,
            [{"attribute": "ImageQuality", "value": "original"}])
        sa.clone_project(self.SECOND_PROJECT_NAME, self.PROJECT_NAME, copy_settings=True)
        settings = sa.get_project_settings(self.SECOND_PROJECT_NAME)
        for setting in settings:
            if setting["attribute"] == "ImageQuality":
                assert setting["value"] == "original"
                break
        else:
            raise Exception("Test failed")