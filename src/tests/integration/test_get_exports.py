import os
from os.path import dirname
from pathlib import Path
import tempfile
import time
import  glob
import src.lib.app.superannotate as sa
from src.tests.integration.base import BaseTestCase


class TestGetExports(BaseTestCase):
    PROJECT_NAME = "get_exports"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PTH = "data_set"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    def setUp(self, *args, **kwargs):
        super().setUp()
        sa.upload_images_from_folder_to_project(
            project=self._project["name"], folder_path=self.folder_path
        )
        sa.upload_annotations_from_folder_to_project(project=self._project["name"], folder_path=self.folder_path)

    def test_get_exports(self):
        tmpdir = tempfile.TemporaryDirectory()
        time.sleep(2)
        exports_old = sa.get_exports(self.PROJECT_NAME)
        export = sa.prepare_export(self.PROJECT_NAME)
        time.sleep(2)
        sa.download_export(self.PROJECT_NAME, export["name"], tmpdir.name)
        js = list(glob.glob(tmpdir.name + "/*.json"))

        assert len(js) == 4

        exports_new = sa.get_exports(self.PROJECT_NAME)

        assert len(exports_new) == len(exports_old) + 1





