import os
from unittest import TestCase
import pytest
from src.superannotate import SAClient
sa = SAClient()
from tests import DATA_SET_PATH
import src.superannotate.lib.core as constances


class TestCloneProject(TestCase):
    PROJECT_NAME_1 = "test_create_like_project_1"
    PROJECT_NAME_2 = "test_create_like_project_2"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"
    IMAGE_QUALITY = "original"
    PATH_TO_URLS = "attach_urls.csv"

    def setUp(self, *args, **kwargs):
        self.tearDown()
        self._project_1 = sa.create_project(
            self.PROJECT_NAME_1, self.PROJECT_DESCRIPTION, self.PROJECT_TYPE
        )

    def tearDown(self) -> None:
        sa.delete_project(self.PROJECT_NAME_1)
        sa.delete_project(self.PROJECT_NAME_2)

    def test_create_like_project(self):
        _, _, _ = sa.attach_items(
            self.PROJECT_NAME_1,
            os.path.join(DATA_SET_PATH, self.PATH_TO_URLS),
        )

        sa.create_annotation_class(
            self.PROJECT_NAME_1,
            "rrr",
            "#FFAAFF",
            [
                {
                    "name": "tall",
                    "is_multiselect": 0,
                    "attributes": [{"name": "yes"}, {"name": "no"}],
                },
                {
                    "name": "age",
                    "is_multiselect": 0,
                    "attributes": [{"name": "young"}, {"name": "old"}],
                },
            ],
        )

        sa.set_project_default_image_quality_in_editor(self.PROJECT_NAME_1, self.IMAGE_QUALITY)
        sa.set_project_workflow(
            self.PROJECT_NAME_1,
            [
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
            ],
        )
        new_project = sa.clone_project(
            self.PROJECT_NAME_2, self.PROJECT_NAME_1, copy_contributors=True
        )
        self.assertEqual(new_project['upload_state'], constances.UploadState.INITIAL.name)

        new_settings = sa.get_project_settings(self.PROJECT_NAME_2)
        image_quality = None
        for setting in new_settings:
            if setting["attribute"].lower() == "imagequality":
                image_quality = setting["value"]
                break
        self.assertEqual(image_quality, self.IMAGE_QUALITY)
        self.assertEqual(new_project["description"], self.PROJECT_DESCRIPTION)
        self.assertEqual(new_project["type"].lower(), "vector")

        ann_classes = sa.search_annotation_classes(self.PROJECT_NAME_2)
        self.assertEqual(len(ann_classes), 1)
        self.assertEqual(ann_classes[0]["name"], "rrr")
        new_workflow = sa.get_project_workflow(self.PROJECT_NAME_2)
        self.assertEqual(len(new_workflow), 1)
        self.assertEqual(new_workflow[0]["className"], "rrr")
        self.assertEqual(new_workflow[0]["tool"], 3)
        self.assertEqual(len(new_workflow[0]["attribute"]), 2)
        self.assertEqual(new_workflow[0]["attribute"][0]["attribute"]["name"], "young")
        self.assertEqual(
            new_workflow[0]["attribute"][0]["attribute"]["attribute_group"]["name"],
            "age",
        )
        self.assertEqual(new_workflow[0]["attribute"][1]["attribute"]["name"], "yes")
        self.assertEqual(
            new_workflow[0]["attribute"][1]["attribute"]["attribute_group"]["name"],
            "tall",
        )
        self.assertEqual(ann_classes[0]["color"], "#FFAAFF")
        assert new_project["status"], constances.ProjectStatus.NotStarted.name


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

    def test_create_like_project(self):
        sa.create_annotation_class(
            self.PROJECT_NAME_1,
            "rrr",
            "#FFAAFF",
            [
                {
                    "name": "tall",
                    "is_multiselect": 0,
                    "attributes": [{"name": "yes"}, {"name": "no"}],
                },
                {
                    "name": "age",
                    "is_multiselect": 0,
                    "attributes": [{"name": "young"}, {"name": "old"}],
                },
            ],
            "object"
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
        self.assertIn("Workflow copy is deprecated for Document projects.", self._caplog.text)
        assert new_project["status"], constances.ProjectStatus.NotStarted.name