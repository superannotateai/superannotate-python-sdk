import os
from os.path import dirname
from unittest import TestCase

import src.superannotate as sa


class TestCloneProject(TestCase):
    PROJECT_NAME_1 = "test create from full info1"
    PROJECT_NAME_2 = "test create from full info2"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"

    TEST_FOLDER_PATH = "data_set/sample_project_vector"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    @property
    def classes_json(self):
        return f"{self.folder_path}/classes/classes.json"

    def setUp(self, *args, **kwargs):
        self.tearDown()
        self._project_1 = sa.create_project(
            self.PROJECT_NAME_1, self.PROJECT_DESCRIPTION, self.PROJECT_TYPE
        )

    def tearDown(self) -> None:
        sa.delete_project(self.PROJECT_NAME_1)
        sa.delete_project(self.PROJECT_NAME_2)

    def test_create_from_full_info(self):

        sa.upload_images_from_folder_to_project(self.PROJECT_NAME_1, self.folder_path)
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME_1, self.classes_json
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
        team_users = sa.search_team_contributors()
        sa.share_project(self.PROJECT_NAME_1, team_users[0], "QA")

        project_metadata = sa.get_project_metadata(
            self.PROJECT_NAME_1,
            include_annotation_classes=True,
            include_settings=True,
            include_workflow=True,
            include_contributors=True,
        )

        project_metadata["name"] = self.PROJECT_NAME_2

        sa.create_project_from_metadata(project_metadata)
        new_project_metadata = sa.get_project_metadata(
            self.PROJECT_NAME_2,
            include_annotation_classes=True,
            include_settings=True,
            include_workflow=True,
            include_contributors=True,
        )

        for u in new_project_metadata["contributors"]:
            if u["user_id"] == team_users[0]["id"]:
                break
        else:
            assert False

        self.assertEqual(
            len(new_project_metadata["classes"]), len(project_metadata["classes"]),
        )

        self.assertEqual(
            len(new_project_metadata["settings"]), len(project_metadata["settings"])
        )
        for new_setting in new_project_metadata["settings"]:
            if "attribute" in new_setting and new_setting["attribute"] == "Brightness":
                new_brightness_value = new_setting["value"]
                self.assertEqual(new_brightness_value, brightness_value + 10)

        self.assertEqual(
            len(new_project_metadata["workflows"]), len(project_metadata["workflows"])
        )
