import tempfile
from pathlib import Path
import os
from os.path import join
import json
import pytest
from unittest.mock import patch
from unittest.mock import MagicMock

from src.superannotate import SAClient
sa = SAClient()
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
        return os.path.join(Path(__file__).parent.parent.parent, self.TEST_FOLDER_PATH)

    @pytest.mark.flaky(reruns=3)
    @patch("lib.infrastructure.controller.Reporter")
    def test_annotation_upload(self, reporter):
        reporter_mock = MagicMock()
        reporter.return_value = reporter_mock

        annotation_path = join(self.folder_path, f"{self.IMAGE_NAME}___objects.json")
        sa.upload_image_to_project(self.PROJECT_NAME, join(self.folder_path, self.IMAGE_NAME))
        sa.upload_image_annotations(self.PROJECT_NAME, self.IMAGE_NAME, annotation_path)

        from collections import defaultdict
        call_groups = defaultdict(list)
        reporter_calls = reporter_mock.method_calls
        for call in reporter_calls:
            call_groups[call[0]].append(call[1])
        self.assertEqual(len(call_groups["log_warning"]), len(call_groups["store_message"]))
        with tempfile.TemporaryDirectory() as tmp_dir:
            sa.download_image_annotations(self.PROJECT_NAME, self.IMAGE_NAME, tmp_dir)
            origin_annotation = json.load(open(annotation_path))
            annotation = json.load(open(join(tmp_dir, f"{self.IMAGE_NAME}___objects.json")))
            self.assertEqual(
                [i["attributes"]for i in annotation["instances"]],
                [i["attributes"]for i in origin_annotation["instances"]]
            )

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
                    len([i["attributes"] for i in annotation["instances"]]),
                    len([i["attributes"] for i in origin_annotation["instances"]])
                )
