import copy
from unittest import TestCase

import src.superannotate.lib.core as constances
from src.superannotate import AppException
from src.superannotate import SAClient


sa = SAClient()


class ProjectCreateBaseTestCase(TestCase):
    PROJECT = "test_vector_project"
    CLASSES = [
        {
            "type": 1,
            "name": "Personal vehicle",
            "color": "#ecb65f",
            "attribute_groups": [
                {
                    "name": "test",
                    "group_type": "checklist",
                    "attributes": [
                        {"name": "Car"},
                        {"name": "Track"},
                        {"name": "Bus"},
                    ],
                    "default_value": ["Bus"],
                }
            ],
        }
    ]
    WORKFLOWS = [
        {
            "step": 1,
            "className": "Personal vehicle",
            "tool": 3,
            "attribute": [
                {
                    "attribute": {
                        "name": "Car",
                        "attribute_group": {"name": "test"},
                    }
                },
                {
                    "attribute": {
                        "name": "Bus",
                        "attribute_group": {"name": "test"},
                    }
                },
            ],
        },
        {
            "step": 2,
            "className": "Personal vehicle",
            "tool": 3,
            "attribute": [
                {
                    "attribute": {
                        "name": "Track",
                        "attribute_group": {"name": "test"},
                    }
                },
                {
                    "attribute": {
                        "name": "Bus",
                        "attribute_group": {"name": "test"},
                    }
                },
            ],
        },
    ]

    def setUp(self, *args, **kwargs):
        self.tearDown()

    def tearDown(self) -> None:
        try:
            sa.delete_project(self.PROJECT)
        except AppException:
            ...


class TestCreateVectorProject(ProjectCreateBaseTestCase):
    PROJECT_TYPE = "Vector"

    def test_create_project_datetime(self):
        project = sa.create_project(self.PROJECT, "desc", self.PROJECT_TYPE)
        metadata = sa.get_project_metadata(project["name"])
        assert "Z" not in metadata["createdAt"]

    def test_create_project_with_wrong_type(self):
        with self.assertRaisesRegexp(
            AppException,
            "Available values are 'Vector', 'Pixel', 'Video', 'Document', 'Tiled', 'PointCloud', 'GenAI'.",
        ):
            sa.create_project(self.PROJECT, "desc", "wrong_type")

    def test_create_project_with_settings(self):
        sa.create_project(
            self.PROJECT,
            "desc",
            self.PROJECT_TYPE,
            [{"attribute": "ImageQuality", "value": "original"}],
        )
        project = sa.get_project_metadata(self.PROJECT, include_settings=True)
        for setting in project["settings"]:
            if setting["attribute"] == "ImageQuality":
                assert setting["value"] == "original"

    def test_create_project_with_classes_and_workflows(self):
        project = sa.create_project(
            self.PROJECT,
            "desc",
            self.PROJECT_TYPE,
            classes=self.CLASSES,
        )
        sa.set_project_workflow(self.PROJECT,  self.WORKFLOWS)
        assert len(project["classes"]) == 1
        assert len(project["classes"][0]["attribute_groups"]) == 1
        assert len(project["classes"][0]["attribute_groups"][0]["attributes"]) == 3
        steps = sa.get_project_steps(self.PROJECT)
        assert len(steps) == 2
        assert steps[0]["className"] == self.CLASSES[0]["name"]
        assert steps[0]["attribute"][0]["attribute"]["name"] == "Car"
        assert steps[0]["attribute"][1]["attribute"]["name"] == "Bus"
        assert steps[1]["attribute"][0]["attribute"]["name"] == "Track"
        assert steps[1]["attribute"][1]["attribute"]["name"] == "Bus"

    def test_create_project_with_workflow_and_wrong_classes(self):
        try:
            workflows = copy.copy(self.WORKFLOWS)
            workflows[0]["className"] = "1"
            workflows[1]["className"] = "2"
            sa.create_project(
                self.PROJECT,
                "desc",
                self.PROJECT_TYPE,
                classes=self.CLASSES,

            )
            sa.set_project_steps(self.PROJECT, self.WORKFLOWS)
        except AppException as e:
            assert str(e) == "There are no [1, 2] classes created in the project."


class TestCreateVideoProject(ProjectCreateBaseTestCase):
    PROJECT = "test_video_project"
    PROJECT_TYPE = "Video"

    def test_create_video_project_frame_mode_off(self):
        sa.create_project(
            self.PROJECT,
            "desc",
            self.PROJECT_TYPE,
        )
        project = sa.get_project_metadata(self.PROJECT, include_settings=True)
        self.assertEqual(project["upload_state"], constances.UploadState.EXTERNAL.name)
        for setting in project["settings"]:
            if setting["attribute"] == "FrameMode":
                assert not setting["value"]

    def test_create_video_project_frame_mode_on(self):
        sa.create_project(
            self.PROJECT,
            "desc",
            self.PROJECT_TYPE,
            [{"attribute": "FrameRate", "value": 1.0}],
        )
        project = sa.get_project_metadata(self.PROJECT, include_settings=True)
        for setting in project["settings"]:
            if setting["attribute"] == "FrameRate":
                assert setting["value"] == 1.0
