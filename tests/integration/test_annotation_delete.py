import os
from os.path import dirname

import src.superannotate as sa
from tests.integration.base import BaseTestCase


class TestAnnotationDelete(BaseTestCase):
    PROJECT_NAME_ = "TestAnnotationDelete"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    @property
    def classes_json(self):
        return os.path.join(
            dirname(dirname(__file__)),
            "data_set/sample_project_vector/classes/classes.json",
        )

    def test_delete_annotations(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, f"{self.folder_path}"
        )
        sa.delete_annotations(self.PROJECT_NAME)

    # def test_delete_annotations_from_