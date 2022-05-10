import os
from pathlib import Path

from src.superannotate import SAClient
sa = SAClient()
from tests.integration.base import BaseTestCase


class TestEntitiesSearchVector(BaseTestCase):
    PROJECT_NAME = "TestEntitiesSearchVector"
    PROJECT_DESCRIPTION = "TestEntitiesSearchVector"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    TEST_QUERY = "instance(type =bbox )"
    TEST_INVALID_QUERY = "!instance(type =bbox )!"

    @property
    def folder_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.TEST_FOLDER_PATH)

    def test_query(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        _, _, _ = sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path
        )

        entities = sa.query(self.PROJECT_NAME, self.TEST_QUERY)
        self.assertEqual(len(entities), 1)
        assert all([entity["path"] is None for entity in entities])

    def test_validate_saqul_query(self):
        try:
            self.assertRaises(Exception, sa.query(self.PROJECT_NAME, self.TEST_INVALID_QUERY))
        except Exception as e:
            self.assertEqual(str(e), "Incorrect query.")


class TestUnsupportedProjectEntitiesSearchVector(BaseTestCase):
    PROJECT_NAME = "TestUnsupportedProjectEntitiesSearchVector"
    PROJECT_DESCRIPTION = "TestEntitiesSearchVector"
    PROJECT_TYPE = "Pixel"
    TEST_QUERY = "instance(type =bbox )"
    TEST_INVALID_QUERY = "!instance(type =bbox )!"

    @property
    def folder_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.TEST_FOLDER_PATH)

    def test_query(self):
        try:
            sa.query(self.PROJECT_NAME, self.TEST_QUERY)
        except Exception as e:
            self.assertEqual(str(e), "Unsupported project type.")
