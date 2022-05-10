import os
import tempfile
from os.path import dirname

from src.superannotate import SAClient
sa = SAClient()
from tests.integration.base import BaseTestCase


class TestExportImport(BaseTestCase):
    PROJECT_NAME = "export_import"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PTH = "data_set"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    @property
    def classes_path(self):
        return os.path.join(
            dirname(dirname(__file__)), self.TEST_FOLDER_PATH, "classes/classes.json"
        )

    def test_export_import(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress",
        )

        with tempfile.TemporaryDirectory() as tmpdir_name:
            export = sa.prepare_export(self.PROJECT_NAME, include_fuse=True)
            sa.download_export(self.PROJECT_NAME, export, tmpdir_name)
            self.assertEqual(len(os.listdir(tmpdir_name)), 13)
