import glob
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
        self._attach_items()
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        _, _, _ = sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            annotations_path = sa.download_annotations(
                f"{self.PROJECT_NAME}", temp_dir, [self.IMAGE_NAME]
            )
            self.assertEqual(len(os.listdir(temp_dir)), 2)
            with open(
                f"{self.folder_path}/example_without_postfixes/{self.IMAGE_NAME}.json"
            ) as pre_annotation_file, open(
                f"{annotations_path}/{self.IMAGE_NAME}.json"
            ) as post_annotation_file:
                pre_annotation_data = json.load(pre_annotation_file)
                post_annotation_data = json.load(post_annotation_file)
                self.assertEqual(
                    len(pre_annotation_data["instances"]),
                    len(post_annotation_data["instances"]),
                )

    @pytest.mark.flaky(reruns=3)
    def test_download_annotations_from_folders(self):
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_NAME)
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_NAME_2)
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        for folder in [self.FOLDER_NAME, self.FOLDER_NAME_2, ""]:
            sa.upload_images_from_folder_to_project(
                f"{self.PROJECT_NAME}{'/' + folder if folder else ''}",
                self.folder_path,
                annotation_status="InProgress",
            )
            _, _, _ = sa.upload_annotations_from_folder_to_project(
                f"{self.PROJECT_NAME}{'/' + folder if folder else ''}", self.folder_path
            )
        with tempfile.TemporaryDirectory() as temp_dir:
            annotations_path = sa.download_annotations(
                f"{self.PROJECT_NAME}", temp_dir, recursive=True
            )
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

    @pytest.mark.flaky(reruns=3)
    def test_download_annotations_from_folders_mul(self):
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_NAME)
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_NAME_2)
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        sa.attach_items(
            f"{self.PROJECT_NAME}/{self.FOLDER_NAME}",
            [
                {"name": f"example_image_{i}.jpg", "url": f"url_{i}"}
                for i in range(1, 5)
            ],  # noqa
        )
        sa.attach_items(
            self.PROJECT_NAME,
            [
                {"name": f"example_image_{i}.jpg", "url": f"url_{i}"}
                for i in range(1, 19)
            ],  # noqa
        )
        sa.attach_items(
            f"{self.PROJECT_NAME}/{self.FOLDER_NAME_2}",
            [
                {"name": f"example_image_{i}.jpg", "url": f"url_{i}"}
                for i in range(1, 10)
            ],  # noqa
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            annotations_path = sa.download_annotations(
                self.PROJECT_NAME, temp_dir, recursive=True
            )
            count = len(
                [i for i in glob.iglob(annotations_path + "**/**", recursive=True)]
            )
            assert count == 31 + 5  # folder names and classes

    def test_download_annotations_duplicated_names(self):
        self._attach_items(count=4)
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertLogs("sa", level="INFO") as cm:
                sa.download_annotations(
                    self.PROJECT_NAME, temp_dir, [self.IMAGE_NAME] * 4
                )  # noqa
                assert (
                    "INFO:sa:Dropping duplicates. Found 1/4 unique items." in cm.output
                )


class TestDocumentProjectDownloadAnnotations(BaseTestCase):
    PROJECT_NAME = "Test-document-project-download_annotations"
    FOLDER_NAME = "FOLDER_NAME"
    FOLDER_NAME_2 = "FOLDER_NAME_2"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Document"
    TEST_FOLDER_PATH = "data_set/document_annotation"
    ITEM_NAME = "text_file_example_1"

    @property
    def folder_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.TEST_FOLDER_PATH)

    def test_document_project_download_annotations(self):
        sa.attach_items(
            self.PROJECT_NAME,
            [
                {
                    "name": self.ITEM_NAME,
                    "url": "https://sa-public-files.s3.us-west-2.amazonaws.com/Text+project/text_file_example_1.txt",
                }
            ],
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        _, _, _ = sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            annotations_path = sa.download_annotations(
                f"{self.PROJECT_NAME}", temp_dir, [self.ITEM_NAME]
            )
            self.assertEqual(len(os.listdir(temp_dir)), 2)
            with open(
                f"{self.folder_path}//{self.ITEM_NAME}.json"
            ) as pre_annotation_file, open(
                f"{annotations_path}/{self.ITEM_NAME}.json"
            ) as post_annotation_file:
                pre_annotation_data = json.load(pre_annotation_file)
                post_annotation_data = json.load(post_annotation_file)
                self.assertEqual(
                    len(pre_annotation_data["instances"]),
                    len(post_annotation_data["instances"]),
                )
