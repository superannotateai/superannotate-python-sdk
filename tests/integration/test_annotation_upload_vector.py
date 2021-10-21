import tempfile
from os.path import dirname
from os.path import join
import json
import pytest

import src.superannotate as sa
from tests.integration.base import BaseTestCase


class TestAnnotationUploadVector(BaseTestCase):
    PROJECT_NAME = "TestAnnotationUploadVector"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    S3_FOLDER_PATH = "sample_project_pixel"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    IMAGE_NAME = "example_image_1.jpg"

    @property
    def folder_path(self):
        return join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    @pytest.mark.flaky(reruns=2)
    def test_annotation_upload(self):
        annotation_path = join(self.folder_path, f"{self.IMAGE_NAME}___objects.json")
        sa.upload_image_to_project(self.PROJECT_NAME, join(self.folder_path, self.IMAGE_NAME))
        sa.upload_image_annotations(self.PROJECT_NAME, self.IMAGE_NAME, annotation_path)
        with tempfile.TemporaryDirectory() as tmp_dir:
            sa.download_image_annotations(self.PROJECT_NAME, self.IMAGE_NAME, tmp_dir)
            origin_annotation = json.load(open(annotation_path))
            annotation = json.load(open(join(tmp_dir, f"{self.IMAGE_NAME}___objects.json")))
            self.assertEqual(
                [i["attributes"]for i in annotation["instances"]],
                [i["attributes"]for i in origin_annotation["instances"]]
            )

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
        images = sa.search_images(self.PROJECT_NAME)
        with tempfile.TemporaryDirectory() as tmp_dir:
            for image_name in images:
                annotation_path = join(self.folder_path, f"{image_name}___objects.json")
                sa.download_image_preannotations(self.PROJECT_NAME, image_name, tmp_dir)
                origin_annotation = json.load(open(annotation_path))
                annotation = json.load(open(join(tmp_dir, f"{image_name}___objects.json")))
                self.assertEqual(
                    len([i["attributes"] for i in annotation["instances"]]),
                    len([i["attributes"] for i in origin_annotation["instances"]])
                )