from unittest import TestCase

from src.superannotate import SAClient
sa = SAClient()
from src.superannotate import AppException


class BaseTestCase(TestCase):
    PROJECT_NAME = "TestSettings"
    SECOND_PROJECT_NAME = "SecondTestSettings"
    PROJECT_DESCRIPTION = "TestSettings"

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


class TestSettings(BaseTestCase):
    PROJECT_NAME = "TestSettings"
    SECOND_PROJECT_NAME = "SecondTestSettings"
    PROJECT_TYPE = "Vector"

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

    def test_frame_rate_invalid_range_value(self):
        with self.assertRaisesRegexp(AppException, "FrameRate is available only for Video projects"):
            sa.create_project(
                self.PROJECT_NAME,
                self.PROJECT_DESCRIPTION,
                self.PROJECT_TYPE,
                [{"attribute": "FrameRate", "value": 1.0}])


class TestVideoSettings(BaseTestCase):
    PROJECT_NAME = "TestVideoSettings12"
    SECOND_PROJECT_NAME = "TestVideoSettings2"
    PROJECT_TYPE = "Video"

    def test_frame_rate(self):
        sa.create_project(
            self.PROJECT_NAME,
            self.PROJECT_DESCRIPTION,
            self.PROJECT_TYPE,
            [{"attribute": "FrameRate", "value": 1}])
        settings = sa.get_project_settings(self.PROJECT_NAME)
        for setting in settings:
            if setting["attribute"] == "FrameRate":
                assert setting["value"] == 1
                break
            elif setting["attribute"] == "FrameMode":
                assert setting["value"]
                break
        else:
            raise Exception("Test failed")

    def test_frame_rate_float(self):
        sa.create_project(
            self.PROJECT_NAME,
            self.PROJECT_DESCRIPTION,
            self.PROJECT_TYPE,
            [{"attribute": "FrameRate", "value": 1.3}])
        settings = sa.get_project_settings(self.PROJECT_NAME)
        for setting in settings:
            if setting["attribute"] == "FrameRate":
                assert setting["value"] == 1.3
                break
            elif setting["attribute"] == "FrameMode":
                assert setting["value"]
                break
        else:
            raise Exception("Test failed")

    def test_frame_rate_invalid_range_value(self):
        with self.assertRaisesRegexp(AppException, "The FrameRate value range is between 0.001 - 120"):
            sa.create_project(
                self.PROJECT_NAME,
                self.PROJECT_DESCRIPTION,
                self.PROJECT_TYPE,
                [{"attribute": "FrameRate", "value": 1.00003}])

    def test_frame_rate_invalid_str_value(self):
        with self.assertRaisesRegexp(AppException, "The FrameRate value should be float"):
            sa.create_project(
                self.PROJECT_NAME,
                self.PROJECT_DESCRIPTION,
                self.PROJECT_TYPE,
                [{"attribute": "FrameRate", "value": "1"}])

    def test_frames_reset(self):
        sa.create_project(
            self.PROJECT_NAME,
            self.PROJECT_DESCRIPTION,
            self.PROJECT_TYPE,
            [{"attribute": "FrameRate", "value": 1.3}])
        sa.rename_project(self.PROJECT_NAME, self.SECOND_PROJECT_NAME)
        settings = sa.get_project_settings(self.SECOND_PROJECT_NAME)
        for setting in settings:
            if setting["attribute"] == "FrameRate":
                assert setting["value"] == 1.3
                break
            elif setting["attribute"] == "FrameMode":
                assert setting["value"]
                break
        else:
            raise Exception("Test failed")
