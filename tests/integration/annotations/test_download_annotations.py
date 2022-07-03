import json
import os
import tempfile
from pathlib import Path

import pytest

from src.superannotate import SAClient
from tests.integration.base import BaseTestCase


sa = SAClient()


class TestDownloadAnnotations(BaseTestCase):
    PROJECT_NAME = "Test-download_annotations"
    FOLDER_NAME = "FOLDER_NAME"
    FOLDER_NAME_2 = "FOLDER_NAME_2"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    IMAGE_NAME = "example_image_1.jpg"

    @property
    def folder_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.TEST_FOLDER_PATH)

    @pytest.mark.flaky(reruns=3)
    def test_download_annotations(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        _, _, _ = sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            annotations_path = sa.download_annotations(f"{self.PROJECT_NAME}", temp_dir, [self.IMAGE_NAME])
            self.assertEqual(len(os.listdir(temp_dir)), 1)
            with open(f"{self.folder_path}/{self.IMAGE_NAME}___objects.json", "r") as pre_annotation_file, open(
                    f"{annotations_path}/{self.IMAGE_NAME}___objects.json") as post_annotation_file:
                pre_annotation_data = json.load(pre_annotation_file)
                post_annotation_data = json.load(post_annotation_file)
                self.assertEqual(len(pre_annotation_data["instances"]), len(post_annotation_data["instances"]))

    @pytest.mark.flaky(reruns=3)
    def test_download_annotations_from_folders(self):
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_NAME)
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_NAME_2)
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        for folder in [self.FOLDER_NAME, self.FOLDER_NAME_2, ""]:
            sa.upload_images_from_folder_to_project(
                f"{self.PROJECT_NAME}{'/' + folder if folder else ''}", self.folder_path, annotation_status="InProgress"
            )
            _, _, _ = sa.upload_annotations_from_folder_to_project(
                f"{self.PROJECT_NAME}{'/' + folder if folder else ''}", self.folder_path
            )
        with tempfile.TemporaryDirectory() as temp_dir:
            annotations_path = sa.download_annotations(f"{self.PROJECT_NAME}", temp_dir, recursive=True)
            self.assertEqual(len(os.listdir(annotations_path)), 7)

    @pytest.mark.flaky(reruns=3)
    def test_download_empty_annotations_from_folders(self):
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_NAME)
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_NAME_2)
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            annotations_path = sa.download_annotations(f"{self.PROJECT_NAME}", temp_dir)
            self.assertEqual(len(os.listdir(annotations_path)), 1)