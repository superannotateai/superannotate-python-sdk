from pathlib import Path
import os
from os.path import join
import pytest
from unittest.mock import patch
from unittest.mock import MagicMock

from src.superannotate import SAClient
sa = SAClient()
import src.superannotate.lib.core as constances
from tests.integration.base import BaseTestCase


class TestAnnotationUploadStatusChangeVector(BaseTestCase):
    PROJECT_NAME = "TestAnnotationUploadStatusChangeVector"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    S3_FOLDER_PATH = "sample_project_pixel"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    IMAGE_NAME = "example_image_1.jpg"

    @property
    def folder_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.TEST_FOLDER_PATH)

    @pytest.mark.flaky(reruns=2)
    @patch("lib.infrastructure.controller.Reporter")
    def test_upload_annotations_from_folder_to_project__upload_status(self, reporter):
        reporter_mock = MagicMock()
        reporter.return_value = reporter_mock
        sa.upload_image_to_project(self.PROJECT_NAME, join(self.folder_path, self.IMAGE_NAME))
        sa.upload_annotations_from_folder_to_project(self.PROJECT_NAME, self.folder_path)
        self.assertEqual(
            constances.AnnotationStatus.IN_PROGRESS.name,
            sa.get_item_metadata(self.PROJECT_NAME, self.IMAGE_NAME)["annotation_status"]
        )

    @pytest.mark.flaky(reruns=2)
    @patch("lib.infrastructure.controller.Reporter")
    def test_upload_preannotations_from_folder_to_project__upload_status(self, reporter):
        reporter_mock = MagicMock()
        reporter.return_value = reporter_mock
        sa.upload_image_to_project(self.PROJECT_NAME, join(self.folder_path, self.IMAGE_NAME))
        sa.upload_preannotations_from_folder_to_project(self.PROJECT_NAME, self.folder_path)
        self.assertEqual(
            constances.AnnotationStatus.IN_PROGRESS.name,
            sa.get_item_metadata(self.PROJECT_NAME, self.IMAGE_NAME)["annotation_status"]
        )

    @pytest.mark.flaky(reruns=2)
    @patch("lib.infrastructure.controller.Reporter")
    def test_upload_image_annotations__upload_status(self, reporter):
        reporter_mock = MagicMock()
        reporter.return_value = reporter_mock
        annotation_path = join(self.folder_path, f"{self.IMAGE_NAME}___objects.json")
        sa.upload_image_to_project(self.PROJECT_NAME, join(self.folder_path, self.IMAGE_NAME))
        sa.upload_image_annotations(self.PROJECT_NAME, self.IMAGE_NAME, annotation_path)
        self.assertEqual(
            constances.AnnotationStatus.IN_PROGRESS.name,
            sa.get_item_metadata(self.PROJECT_NAME, self.IMAGE_NAME)["annotation_status"]
        )

    @pytest.mark.flaky(reruns=2)
    @patch("lib.infrastructure.controller.Reporter")
    def test_add_annotation_bbox_to_image__annotation_status(self, reporter):
        reporter_mock = MagicMock()
        reporter.return_value = reporter_mock
        sa.upload_image_to_project(self.PROJECT_NAME, join(self.folder_path, self.IMAGE_NAME))
        sa.add_annotation_bbox_to_image(self.PROJECT_NAME, self.IMAGE_NAME, [1, 2, 3, 4], "bbox")
        self.assertEqual(
            constances.AnnotationStatus.IN_PROGRESS.name,
            sa.get_item_metadata(self.PROJECT_NAME, self.IMAGE_NAME)["annotation_status"]
        )

    @pytest.mark.flaky(reruns=2)
    @patch("lib.infrastructure.controller.Reporter")
    def test_add_annotation_comment_to_image__annotation_status(self, reporter):
        reporter_mock = MagicMock()
        reporter.return_value = reporter_mock
        sa.upload_image_to_project(self.PROJECT_NAME, join(self.folder_path, self.IMAGE_NAME))
        sa.add_annotation_comment_to_image(
            self.PROJECT_NAME,
            self.IMAGE_NAME,
            "Hello World!",
            [1, 2],
            "user@superannoate.com")
        self.assertEqual(
            constances.AnnotationStatus.IN_PROGRESS.name,
            sa.get_item_metadata(self.PROJECT_NAME, self.IMAGE_NAME)["annotation_status"]
        )
