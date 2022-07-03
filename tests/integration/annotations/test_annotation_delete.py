import os
from pathlib import Path

import pytest

from src.superannotate import SAClient
sa = SAClient()
from tests.integration.base import BaseTestCase


class TestAnnotationDelete(BaseTestCase):
    PROJECT_NAME = "TestAnnotationDelete"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_NAME = "folder"
    TEST_FOLDER_PATH = "data_set/sample_project_vector_single_image"
    EXAMPLE_IMAGE_1 = "example_image_1.jpg"
    EXAMPLE_IMAGE_2 = "example_image_2.jpg"

    @property
    def folder_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.TEST_FOLDER_PATH)

    @property
    def classes_json(self):
        return os.path.join(Path(__file__).parent.parent.parent,
                            "data_set/sample_project_vector/classes/classes.json",
                            )

    def test_delete_annotations(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.folder_path + "/classes/classes.json"
        )
        sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, f"{self.folder_path}"
        )

        sa.delete_annotations(self.PROJECT_NAME)
        annotations = sa.get_annotations(self.PROJECT_NAME, [self.EXAMPLE_IMAGE_1])
        del annotations[0]["metadata"]["projectId"]
        assert annotations == [
            {'metadata': {'name': 'example_image_1.jpg', 'height': 683, 'width': 1024,
                          'isPredicted': False, 'status': 'NotStarted', 'pinned': False, 'annotatorEmail': None,
                          'qaEmail': None}, 'instances': [], 'tags': [], 'comments': []}
        ]

    def test_delete_annotations_by_name(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.folder_path + "/classes/classes.json"
        )
        sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, f"{self.folder_path}"
        )
        sa.delete_annotations(self.PROJECT_NAME, [self.EXAMPLE_IMAGE_1])
        annotations = sa.get_annotations(self.PROJECT_NAME, [self.EXAMPLE_IMAGE_1])
        del annotations[0]["metadata"]["projectId"]
        assert annotations == [
            {'metadata': {'name': 'example_image_1.jpg', 'height': 683, 'width': 1024,
                          'isPredicted': False, 'status': 'NotStarted', 'pinned': False, 'annotatorEmail': None,
                          'qaEmail': None}, 'instances': [], 'tags': [], 'comments': []}
        ]

    def test_delete_annotations_by_not_existing_name(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.folder_path + "/classes/classes.json"
        )
        sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, f"{self.folder_path}"
        )
        self.assertRaises(Exception, sa.delete_annotations, self.PROJECT_NAME, [self.EXAMPLE_IMAGE_2])

    @pytest.mark.flaky(reruns=2)
    def test_delete_annotations_wrong_path(self):
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME)
        sa.upload_images_from_folder_to_project(
            f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME}", self.folder_path, annotation_status="InProgress"
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.folder_path + "/classes/classes.json"
        )
        sa.upload_annotations_from_folder_to_project(
            f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME}", f"{self.folder_path}"
        )
        self.assertRaises(Exception, sa.delete_annotations, self.PROJECT_NAME, [self.EXAMPLE_IMAGE_1])

    def test_delete_annotations_from_folder(self):
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME)

        sa.upload_images_from_folder_to_project(
            f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME}", self.folder_path, annotation_status="InProgress"
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.folder_path + "/classes/classes.json"
        )
        sa.upload_annotations_from_folder_to_project(
            f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME}", f"{self.folder_path}"
        )
        sa.delete_annotations(f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME}", [self.EXAMPLE_IMAGE_1])
        annotations = sa.get_annotations(self.PROJECT_NAME, [self.EXAMPLE_IMAGE_1])
        assert len(annotations) == 0
