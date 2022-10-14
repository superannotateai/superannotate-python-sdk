from unittest import TestCase

from src.superannotate import SAClient

sa = SAClient()


class CreateProjectFromMetadata(TestCase):
    PROJECT_1 = "pr_1"
    PROJECT_2 = "pr_2"

    def setUp(self) -> None:
        self.tearDown()

    def tearDown(self) -> None:
        for project_name in self.PROJECT_1, self.PROJECT_2:
            try:
                sa.delete_project(project_name)
            except Exception:
                pass

    def test_create_project_with_default_attribute(self):
        sa.create_project(self.PROJECT_1, project_type="Vector", project_description="Desc")
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_1,
            classes_json=[
                {
                    "name": "Personal vehicle",
                    "color": "#ecb65f",
                    "count": 25,
                    "createdAt": "2020-10-12T11:35:20.000Z",
                    "updatedAt": "2020-10-12T11:48:19.000Z",
                    "attribute_groups": [
                        {
                            "name": "test",
                            "attributes": [{"name": "Car"}, {"name": "Track"}, {"name": "Bus"}],
                            "default_value": "Bus",
                            "is_multiselect": 0
                        }
                    ]
                }
            ]
        )
        pr_1_metadata = sa.get_project_metadata(self.PROJECT_1, include_annotation_classes=True)
        pr_1_metadata["name"] = self.PROJECT_2
        sa.create_project_from_metadata(pr_1_metadata)
        pr_2_metadata = sa.get_project_metadata(self.PROJECT_2, include_annotation_classes=True)
        assert pr_2_metadata["classes"][0]["attribute_groups"][0]["default_value"] == "Bus"
        assert "is_multiselect" not in pr_2_metadata["classes"][0]["attribute_groups"][0]

    def test_metadata_create_workflow(self):
        sa.create_project(self.PROJECT_1, project_type="Vector", project_description="Desc")
        sa.create_annotation_class(
            self.PROJECT_1,
            "class1",
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
        sa.create_annotation_class(
            self.PROJECT_1,
            "class2",
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
        sa.set_project_workflow(
            self.PROJECT_1,
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
                }
            ],
        )

        pr_1_metadata = sa.get_project_metadata(self.PROJECT_1, include_annotation_classes=True, include_workflow=True)
        pr_1_metadata["name"] = self.PROJECT_2
        sa.create_project_from_metadata(pr_1_metadata)
        pr_2_metadata = sa.get_project_metadata(self.PROJECT_2, include_workflow=True)
        assert pr_2_metadata["workflows"][0]["className"] == "class1"
        assert pr_2_metadata["workflows"][1]["className"] == "class2"
        self.assertEqual(pr_2_metadata["classes"][0]['className'], "class1")
        self.assertEqual(pr_2_metadata["classes"][1]['className'], "class2")
