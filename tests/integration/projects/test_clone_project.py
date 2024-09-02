import os
from unittest import TestCase

import pytest
import src.superannotate.lib.core as constances
from src.superannotate import SAClient
from superannotate import AppException
from tests import DATA_SET_PATH

sa = SAClient()


class TestCloneProject(TestCase):
    PROJECT_NAME_1 = "test_create_like_project_1"
    PROJECT_NAME_2 = "test_create_like_project_2"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"
    IMAGE_QUALITY = "original"
    PATH_TO_URLS = "attach_urls.csv"
    ANNOTATION_CLASSES = [
        {
            "name": "tall",
            "attributes": [{"name": "yes"}, {"name": "no"}],
        },
        {
            "name": "age",
            "attributes": [{"name": "young"}, {"name": "old"}],
        },
    ]
    WORKFLOWS = [
        {
            "step": 1,
            "className": "rrr",
            "tool": 3,
            "attribute": [
                {
                    "attribute": {
                        "name": "young",
                        "attribute_group": {"name": "age"},
                    }
                },
                {
                    "attribute": {
                        "name": "yes",
                        "attribute_group": {"name": "tall"},
                    }
                },
            ],
        }
    ]

    def setUp(self, *args, **kwargs):
        self.tearDown()
        self._project_1 = sa.create_project(
            self.PROJECT_NAME_1, self.PROJECT_DESCRIPTION, self.PROJECT_TYPE
        )

    def tearDown(self) -> None:
        sa.delete_project(self.PROJECT_NAME_1)
        sa.delete_project(self.PROJECT_NAME_2)

    def test_clone_project(self):
        sa.attach_items(
            self.PROJECT_NAME_1,
            os.path.join(DATA_SET_PATH, self.PATH_TO_URLS),
        )

        sa.create_annotation_class(
            self.PROJECT_NAME_1,
            "rrr",
            "#FFAAFF",
            self.ANNOTATION_CLASSES,
        )

        sa.set_project_default_image_quality_in_editor(
            self.PROJECT_NAME_1, self.IMAGE_QUALITY
        )
        sa.set_project_workflow(
            self.PROJECT_NAME_1,
            self.WORKFLOWS,
        )
        new_project = sa.clone_project(
            project_name=self.PROJECT_NAME_2,
            from_project=self.PROJECT_NAME_1,
            copy_contributors=True,
            copy_workflow=True,
            copy_annotation_classes=True,
        )
        self.assertEqual(
            new_project["upload_state"], constances.UploadState.INITIAL.name
        )
        new_settings = sa.get_project_settings(self.PROJECT_NAME_2)
        for setting in new_settings:
            if setting["attribute"].lower() == "imageQuality".lower():
                self.assertEqual(setting["value"], self.IMAGE_QUALITY)
                break
        self.assertEqual(new_project["description"], self.PROJECT_DESCRIPTION)
        self.assertEqual(new_project["type"].lower(), "vector")

        ann_classes = sa.search_annotation_classes(self.PROJECT_NAME_2)
        self.assertEqual(len(ann_classes), 1)
        self.assertEqual(ann_classes[0]["name"], "rrr")
        assert (
            new_project["workflow_id"]
            == sa.get_project_metadata(self.PROJECT_NAME_1)["workflow_id"]
        )


class TestCloneProjectAttachedUrls(TestCase):
    PROJECT_NAME_1 = "TestCloneProjectAttachedUrls_1"
    PROJECT_NAME_2 = "TestCloneProjectAttachedUrls_2"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Document"

    @pytest.fixture(autouse=True)
    def inject_fixtures(self, caplog):
        self._caplog = caplog

    def setUp(self, *args, **kwargs):
        self.tearDown()
        self._project_1 = sa.create_project(
            self.PROJECT_NAME_1, self.PROJECT_DESCRIPTION, self.PROJECT_TYPE
        )

    def tearDown(self) -> None:
        sa.delete_project(self.PROJECT_NAME_1)
        sa.delete_project(self.PROJECT_NAME_2)

    @pytest.mark.skip(reason="Need to adjust")
    def test_create_like_project(self):
        sa.create_annotation_class(
            self.PROJECT_NAME_1,
            "rrr",
            "#FFAAFF",
            [
                {
                    "name": "tall",
                    "attributes": [{"name": "yes"}, {"name": "no"}],
                },
                {
                    "name": "age",
                    "attributes": [{"name": "young"}, {"name": "old"}],
                },
            ],
            "object",
        )

        new_project = sa.clone_project(
            self.PROJECT_NAME_2, self.PROJECT_NAME_1, copy_contributors=True
        )
        self.assertEqual(new_project["description"], self.PROJECT_DESCRIPTION)
        self.assertEqual(new_project["type"].lower(), "document")

        ann_classes = sa.search_annotation_classes(self.PROJECT_NAME_2)
        self.assertEqual(len(ann_classes), 1)
        self.assertEqual(ann_classes[0]["name"], "rrr")
        self.assertEqual(ann_classes[0]["color"], "#FFAAFF")
        self.assertEqual(ann_classes[0]["type"], "object")
        self.assertIn(
            "Workflow copy is deprecated for Document projects.", self._caplog.text
        )
        assert new_project["status"], constances.ProjectStatus.NotStarted.name


class TestCloneVideoProject(TestCase):
    PROJECT_NAME_1 = "test_create_like_video_project_1"
    PROJECT_NAME_2 = "test_create_like_video_project_2"
    PROJECT_TYPE = "Video"
    PROJECT_DESCRIPTION = "desc"

    def setUp(self, *_, **__):
        self.tearDown()

    def tearDown(self) -> None:
        for i in (self.PROJECT_NAME_1, self.PROJECT_NAME_2):
            try:
                sa.delete_project(i)
            except AppException:
                ...

    def test_clone_video_project(self):
        self._project_1 = sa.create_project(
            self.PROJECT_NAME_1,
            self.PROJECT_DESCRIPTION,
            self.PROJECT_TYPE,
        )
        new_project = sa.clone_project(
            project_name=self.PROJECT_NAME_2,
            from_project=self.PROJECT_NAME_1,
        )
        self.assertEqual(
            new_project["upload_state"], constances.UploadState.EXTERNAL.name
        )
        self.assertEqual(new_project["name"], self.PROJECT_NAME_2)
        self.assertEqual(new_project["type"].lower(), "video")
        self.assertEqual(new_project["description"], self._project_1["description"])

    def test_clone_video_project_frame_mode_on(self):
        self._project_1 = sa.create_project(
            self.PROJECT_NAME_1,
            self.PROJECT_DESCRIPTION,
            self.PROJECT_TYPE,
            settings=[{"attribute": "FrameRate", "value": 3}],
        )
        new_project = sa.clone_project(
            project_name=self.PROJECT_NAME_2,
            from_project=self.PROJECT_NAME_1,
            copy_settings=True,
        )

        self.assertEqual(new_project["type"].lower(), "video")
        self.assertEqual(new_project["name"], self.PROJECT_NAME_2)

        new_settings = sa.get_project_settings(self.PROJECT_NAME_2)
        for i in new_settings:
            if i["attribute"] == "FrameRate":
                assert i["value"] == 3
            elif i["attribute"] == "FrameMode":
                assert i["value"]

    def test_clone_video_project_frame_mode_off(self):
        self._project_1 = sa.create_project(
            self.PROJECT_NAME_1,
            self.PROJECT_DESCRIPTION,
            self.PROJECT_TYPE,
        )
        sa.clone_project(
            project_name=self.PROJECT_NAME_2,
            from_project=self.PROJECT_NAME_1,
            copy_settings=True,
        )

        new_settings = sa.get_project_settings(self.PROJECT_NAME_2)
        for s in new_settings:
            if s["attribute"] == "FrameMode":
                assert not s["value"]
