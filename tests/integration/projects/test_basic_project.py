import json
import os
from pathlib import Path

from src.superannotate import SAClient
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestMultimodalProjectBasic(BaseTestCase):
    PROJECT_NAME = "TestMultimodalCreate"
    PROJECT_TYPE = "Multimodal"
    PROJECT_DESCRIPTION = "DESCRIPTION"
    ANNOTATION_PATH = (
        "data_set/sample_project_vector/example_image_1.jpg___objects.json"
    )
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

    def setUp(self, *args, **kwargs):
        self.tearDown()
        self._project = sa.create_project(
            self.PROJECT_NAME,
            self.PROJECT_DESCRIPTION,
            self.PROJECT_TYPE,
            form=self.MULTIMODAL_FORM,
        )

    def tearDown(self) -> None:
        try:
            sa.delete_project(self.PROJECT_NAME)
        except Exception as e:
            print(str(e))

    @property
    def annotation_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.ANNOTATION_PATH)

    def test_search(self):
        projects = sa.search_projects(self.PROJECT_NAME, return_metadata=True)
        assert projects

        sa.create_annotation_class(
            self.PROJECT_NAME,
            "class1",
            "#FFAAFF",
            [
                {
                    "name": "Human",
                    "attributes": [{"name": "yes"}, {"name": "no"}],
                },
                {
                    "name": "age",
                    "attributes": [{"name": "young"}, {"name": "old"}],
                },
            ],
        )
        sa.attach_items(self.PROJECT_NAME, attachments=[{"url": "", "name": "name"}])
        annotation = json.load(open(self.annotation_path))
        annotation["metadata"]["name"] = "name"
        sa.upload_annotations(self.PROJECT_NAME, annotations=[annotation])
        data = sa.get_annotations(self.PROJECT_NAME)
        assert data


class TestProjectBasic(BaseTestCase):
    PROJECT_NAME = "TestWorkflowGet"
    PROJECT_TYPE = "Vector"
    PROJECT_DESCRIPTION = "DESCRIPTION"

    def test_workflow_get(self):
        sa.create_annotation_class(
            self.PROJECT_NAME,
            "class1",
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
        )
        sa.create_annotation_class(
            self.PROJECT_NAME,
            "class2",
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
        )
        sa.set_project_steps(
            self.PROJECT_NAME,
            [
                {
                    "step": 1,
                    "className": "class1",
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
                },
                {
                    "step": 2,
                    "className": "class2",
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
                },
            ],
        )
        workflows = sa.get_project_steps(self.PROJECT_NAME)
        self.assertEqual(workflows[0]["className"], "class1")
        self.assertEqual(workflows[1]["className"], "class2")

    def test_include_complete_image_count(self):
        self._attach_items(count=4)
        sa.set_annotation_statuses(self.PROJECT_NAME, annotation_status="Completed")
        metadata = sa.get_project_metadata(
            self.PROJECT_NAME, include_complete_item_count=True
        )
        assert metadata["completed_items_count"] == 4
