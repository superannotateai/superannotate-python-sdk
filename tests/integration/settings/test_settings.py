from unittest import TestCase

from src.superannotate import AppException
from src.superannotate import SAClient

sa = SAClient()


class BaseTestCase(TestCase):
    PROJECT_NAME = "TestSettings"
    SECOND_PROJECT_NAME = "SecondTestSettings"
    PROJECT_DESCRIPTION = "TestSettings"

    def setUp(self) -> None:
        self.tearDown()

    def tearDown(self) -> None:
        try:
            projects = sa.list_projects(name=self.PROJECT_NAME)
            projects.extend(sa.list_projects(name=self.SECOND_PROJECT_NAME))
            for project in projects:
                try:
                    sa.delete_project(project=project["id"])
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
            self.PROJECT_NAME, self.PROJECT_DESCRIPTION, self.PROJECT_TYPE, []
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
            settings=[
                {"attribute": "ImageQuality", "value": "original"},
                {"attribute": "ItemAutoAssignOrder", "value": 3},
            ],
        )

        settings = sa.get_project_settings(self.PROJECT_NAME)
        assert settings
        for setting in settings:
            if setting["attribute"] == "ImageQuality":
                assert setting["value"] == "original"
            if setting["attribute"] == "ItemAutoAssignOrder":
                assert setting["value"] == 3

    def test_frame_rate_invalid_range_value(self):
        with self.assertRaisesRegex(
            AppException, "FrameRate is available only for Video projects"
        ):
            sa.create_project(
                self.PROJECT_NAME,
                self.PROJECT_DESCRIPTION,
                self.PROJECT_TYPE,
                [{"attribute": "FrameRate", "value": 1.0}],
            )


class TestVideoSettings(BaseTestCase):
    PROJECT_NAME = "TestVideoSettings12"
    SECOND_PROJECT_NAME = "TestVideoSettings2"
    PROJECT_TYPE = "Video"

    def test_frame_rate(self):
        sa.create_project(
            self.PROJECT_NAME,
            self.PROJECT_DESCRIPTION,
            self.PROJECT_TYPE,
            [{"attribute": "FrameRate", "value": 1}],
        )
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
            [{"attribute": "FrameRate", "value": 1.3}],
        )
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
        with self.assertRaisesRegex(
            AppException, "The FrameRate value range is between 0.001 - 120"
        ):
            sa.create_project(
                self.PROJECT_NAME,
                self.PROJECT_DESCRIPTION,
                self.PROJECT_TYPE,
                [{"attribute": "FrameRate", "value": 1.00003}],
            )

    def test_frame_rate_invalid_str_value(self):
        with self.assertRaisesRegex(
            AppException, "The FrameRate value should be float"
        ):
            sa.create_project(
                self.PROJECT_NAME,
                self.PROJECT_DESCRIPTION,
                self.PROJECT_TYPE,
                [{"attribute": "FrameRate", "value": "one"}],
            )

    def test_frames_reset(self):
        sa.create_project(
            self.PROJECT_NAME,
            self.PROJECT_DESCRIPTION,
            self.PROJECT_TYPE,
            [{"attribute": "FrameRate", "value": 1.3}],
        )
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


class TestMMSettings(BaseTestCase):
    """
    Require telemetry access
    """

    PROJECT_NAME = "TestMMSettings"
    SECOND_PROJECT_NAME = "TestMMSettings"
    PROJECT_TYPE = "Multimodal"
    MULTIMODAL_FORM = {
        "components": [
            {
                "id": "r_qx07c6",
                "type": "audio",
                "permissions": [],
                "hasTooltip": False,
                "exclude": False,
                "label": "",
                "value": "",
            }
        ],
        "readme": "",
    }

    def test_mm_project_specific_settings(self):
        sa.create_project(
            self.PROJECT_NAME,
            self.PROJECT_DESCRIPTION,
            self.PROJECT_TYPE,
            settings=[
                {"attribute": "MaxIdleDuration", "value": 612},
                {"attribute": "ImageAutoAssignByCategory", "value": 1},
            ],
            form=self.MULTIMODAL_FORM,
        )
        settings = sa.get_project_settings(self.PROJECT_NAME)
        for setting in settings:
            if setting["attribute"] == "MaxIdleDuration":
                assert setting["value"] == 612
            if setting["attribute"] == "ImageAutoAssignByCategory":
                assert setting["value"] == 1
