import os
import tempfile
from os.path import dirname
from pathlib import Path

import src.superannotate as sa
from tests.integration.base import BaseTestCase


class TestVectorPreAnnotationImage(BaseTestCase):
    PROJECT_NAME = "TestVectorPreAnnotationImage"
    PROJECT_DESCRIPTION = "Example Project test vector pre-annotation upload"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    def test_pre_annotation_folder_upload_download(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        _, _, _ = sa.upload_preannotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path
        )
        count_in = len(list(Path(self.folder_path).glob("*.json")))
        images = sa.search_images(self.PROJECT_NAME)
        with tempfile.TemporaryDirectory() as tmp_dir:
            for image_name in images:
                sa.download_image_preannotations(self.PROJECT_NAME, image_name, tmp_dir)

            count_out = len(list(Path(tmp_dir).glob("*.json")))

            self.assertEqual(count_in, count_out)


class TestVectorAnnotationImage(BaseTestCase):
    PROJECT_NAME = "TestVectorAnnotationImage"
    PROJECT_DESCRIPTION = "Example Project test vector pre-annotation upload"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    def test_pre_annotation_folder_upload_download(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        _, _, _ = sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path
        )
        count_in = len(list(Path(self.folder_path).glob("*.json")))
        images = sa.search_images(self.PROJECT_NAME)
        with tempfile.TemporaryDirectory() as tmp_dir:
            for image_name in images:
                sa.download_image_annotations(self.PROJECT_NAME, image_name, tmp_dir)

            count_out = len(list(Path(tmp_dir).glob("*.json")))

            self.assertEqual(count_in, count_out)
