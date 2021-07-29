import time
from unittest import TestCase

import src.lib.app.superannotate as sa


class TestCloneProject(TestCase):
    PROJECT_NAME_1 = "test_create_like_project_1"
    PROJECT_NAME_2 = "test_create_like_project_2"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"

    def setUp(self, *args, **kwargs):
        self.tearDown()
        time.sleep(1)
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
        )

        old_settings = sa.get_project_settings(self.PROJECT_NAME_1)
        brightness_value = 0
        for setting in old_settings:
            if "attribute" in setting and setting["attribute"] == "Brightness":
                brightness_value = setting["value"]
        sa.set_project_settings(
            self.PROJECT_NAME_1,
            [{"attribute": "Brightness", "value": brightness_value + 10}],
        )
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
        users = sa.search_team_contributors()
        sa.share_project(self.PROJECT_NAME_1, users[0], "QA")

        new_project = sa.clone_project(
            self.PROJECT_NAME_2, self.PROJECT_NAME_1, copy_contributors=True
        )
        self.assertEqual(new_project["description"], self.PROJECT_DESCRIPTION)
        self.assertEqual(new_project["type"].lower(), "vector")
        time.sleep(1)

        ann_classes = sa.search_annotation_classes(self.PROJECT_NAME_2)
        self.assertEqual(len(ann_classes), 1)
        self.assertEqual(ann_classes[0]["name"], "rrr")
        self.assertEqual(ann_classes[0]["color"], "#FFAAFF")

        new_settings = sa.get_project_settings(self.PROJECT_NAME_2)
        for setting in new_settings:
            if "attribute" in setting and setting["attribute"] == "Brightness":
                self.assertEqual(setting["value"], brightness_value + 10)
            break

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

        new_project = sa.get_project_metadata(
            new_project["name"], include_contributors=True
        )
        self.assertEqual(len(new_project["contributors"]), 1)
        self.assertEqual(new_project["contributors"][0]["user_id"], users[0]["id"])
        self.assertEqual(new_project["contributors"][0]["user_role"], "QA")
