import tempfile
from pathlib import Path
import os
from os.path import join
import json
import pytest

from src.superannotate import SAClient
sa = SAClient()
from tests.integration.base import BaseTestCase


class TestAnnotationUploadVector(BaseTestCase):
    PROJECT_NAME = "Test-upload_annotations_from_folder_to_project"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PATH = "data_set/sample_vector_annotations_with_tag_classes"
    IMAGE_NAME = "example_image_1.jpg"

    @property
    def folder_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.TEST_FOLDER_PATH)

    @pytest.mark.flaky(reruns=3)
    def test_annotation_folder_upload_download(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        _, _, _ = sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path
        )
        images = sa.search_items(self.PROJECT_NAME)
        with tempfile.TemporaryDirectory() as tmp_dir:
            for image in images:
                image_name = image["name"]
                annotation_path = join(self.folder_path, f"{image_name}___objects.json")
                sa.download_image_annotations(self.PROJECT_NAME, image_name, tmp_dir)
                origin_annotation = json.load(open(annotation_path))
                annotation = json.load(open(join(tmp_dir, f"{image_name}___objects.json")))
                self.assertEqual(
                    len(annotation["instances"]),
                    len(origin_annotation["instances"])
                )
                self.assertEqual(annotation["instances"][-1]["type"], "tag")
                self.assertEqual(len((annotation["instances"][-1])["attributes"]), 0)
                self.assertEqual(annotation["instances"][-2]["type"], "tag")
                self.assertEqual(len((annotation["instances"][-2])["attributes"]), 0)
