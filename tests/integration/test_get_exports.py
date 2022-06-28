import glob
import os
import tempfile
from os.path import dirname

from src.superannotate import SAClient
from src.superannotate import export_annotation
from tests.integration.base import BaseTestCase

sa = SAClient()


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
        sa.upload_annotations_from_folder_to_project(
            project=self._project["name"], folder_path=self.folder_path
        )

    def test_get_exports(self):
        tmpdir = tempfile.TemporaryDirectory()
        exports_old = sa.get_exports(self.PROJECT_NAME)
        export = sa.prepare_export(self.PROJECT_NAME)
        sa.download_export(self.PROJECT_NAME, export["name"], tmpdir.name)
        js = list(glob.glob(tmpdir.name + "/*.json"))

        assert len(js) == 4

        exports_new = sa.get_exports(self.PROJECT_NAME)

        assert len(exports_new) == len(exports_old) + 1


class TestPixelExportConvert(BaseTestCase):
    PROJECT_NAME = "Pixel_Export"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Pixel"
    TEST_FOLDER_PTH = "data_set"
    TEST_FOLDER_PATH = "data_set/sample_project_pixel"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    def test_convert_pixel_exported_data(self):
        sa.upload_images_from_folder_to_project(self.PROJECT_NAME, self.folder_path)
        sa.upload_annotations_from_folder_to_project(self.PROJECT_NAME, self.folder_path)
        export = sa.prepare_export(self.PROJECT_NAME)
        with tempfile.TemporaryDirectory() as tmp_dir:
            sa.download_export(self.PROJECT_NAME, export["name"], tmp_dir)
            with tempfile.TemporaryDirectory() as converted_data_tmp_dir:
                export_annotation(
                    tmp_dir, converted_data_tmp_dir, "COCO", "export", "Pixel", "panoptic_segmentation"
                )
                self.assertEqual(1, len(list(glob.glob(converted_data_tmp_dir + "/*.json"))))
