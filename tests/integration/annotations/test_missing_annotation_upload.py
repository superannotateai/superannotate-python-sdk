import os
from pathlib import Path

from src.superannotate import SAClient
sa = SAClient()
from tests.integration.base import BaseTestCase


class TestAnnotationUpload(BaseTestCase):
    PROJECT_NAME = "test annotations upload"
    PROJECT_DESCRIPTION = "Example Project test vector missing annotation upload"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PTH = "data_set"
    TEST_FOLDER_PATH = "data_set/sample_project_vector_for_checks"

    @property
    def folder_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.TEST_FOLDER_PATH)

    def test_missing_annotation_upload(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="NotStarted"
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        (
            uploaded,
            could_not_upload,
            missing_images,
        ) = sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path
        )
        self.assertEqual(len(uploaded), 3)
        self.assertEqual(len(could_not_upload), 0)
        self.assertEqual(len(missing_images), 1)

        self.assertTrue(
            any(
                [
                    True
                    for path in uploaded
                    if "sample_project_vector_for_checks/example_image_1.jpg___objects.json"
                    in path
                ]
            )
        )
        self.assertTrue(
            any(
                [
                    True
                    for path in uploaded
                    if "sample_project_vector_for_checks/example_image_2.jpg___objects.json"
                    in path
                ]
            )
        )
        self.assertTrue(
            any(
                [
                    True
                    for path in uploaded
                    if "sample_project_vector_for_checks/example_image_4.jpg___objects.json"
                    in path
                ]
            )
        )
        self.assertTrue(
            any(
                [
                    True
                    for path in missing_images
                    if "sample_project_vector_for_checks/example_image_5.jpg___objects.json"
                    in path
                ]
            )
        )

    def test_missing_pre_annotation_upload(self):

        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="NotStarted"
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        (
            uploaded,
            could_not_upload,
            missing_images,
        ) = sa.upload_preannotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path
        )
        self.assertEqual(len(uploaded), 3)
        self.assertEqual(len(could_not_upload), 0)
        self.assertEqual(len(missing_images), 1)

        self.assertTrue(
            any(
                [
                    True
                    for path in uploaded
                    if "sample_project_vector_for_checks/example_image_1.jpg___objects.json"
                    in path
                ]
            )
        )
        self.assertTrue(
            any(
                [
                    True
                    for path in uploaded
                    if "sample_project_vector_for_checks/example_image_2.jpg___objects.json"
                    in path
                ]
            )
        )
        self.assertTrue(
            any(
                [
                    True
                    for path in uploaded
                    if "sample_project_vector_for_checks/example_image_4.jpg___objects.json"
                    in path
                ]
            )
        )
        self.assertTrue(
            any(
                [
                    True
                    for path in missing_images
                    if "sample_project_vector_for_checks/example_image_5.jpg___objects.json"
                    in path
                ]
            )
        )
