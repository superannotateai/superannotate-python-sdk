import json
import os
import tempfile
from os.path import join

from src.superannotate import AppException
from src.superannotate import SAClient
from tests import DATA_SET_PATH
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestAnnotationUploadVector(BaseTestCase):
    PROJECT_NAME = "PointCloudAnnotationUploadDownload"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "PointCloud"
    TEST_FOLDER_PATH = "sample_project_point_cloud"
    CSV_PATH = f"{TEST_FOLDER_PATH}/urls_template.csv"
    ITEM_NAME = "3d_item_1"

    @property
    def folder_path(self):
        return os.path.join(DATA_SET_PATH, self.TEST_FOLDER_PATH)

    def test_annotation_folder_upload_download(self):
        sa.attach_items(self.PROJECT_NAME, os.path.join(DATA_SET_PATH, self.CSV_PATH))

        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        _, _, _ = sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            for item in sa.search_items(self.PROJECT_NAME):
                item_name = item["name"]
                annotation_path = join(self.folder_path, f"{item_name}.json")
                annotations = sa.get_annotations(self.PROJECT_NAME, [item_name])
                origin_annotation = json.load(open(annotation_path))
                self.assertDictEqual(annotations[0], origin_annotation)
                with self.assertRaisesRegexp(
                    AppException,
                    "The function is not supported for PointCloud projects.",
                ):
                    sa.download_annotations(self.PROJECT_NAME, tmp_dir, [item_name])
