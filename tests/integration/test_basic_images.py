import os
import tempfile
from os.path import dirname
from pathlib import Path

import pytest

from src.superannotate import SAClient
sa = SAClient()
from tests.integration.base import BaseTestCase


class TestVectorAnnotationsWithTag(BaseTestCase):
    PROJECT_NAME = "TestVectorAnnotationsWithTag"
    PROJECT_TYPE = "Vector"
    PROJECT_DESCRIPTION = "TestVectorAnnotationsWithTag"
    TEST_FOLDER_PTH = "data_set/sample_project_vector_with_tag"
    EXAMPLE_IMAGE_1 = "example_image_1.jpg"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PTH)

    @property
    def classes_json_path(self):
        return f"{self.folder_path}/classes/classes.json"

    def test_vector_annotations_with_tag(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.classes_json_path
        )
        sa.upload_image_annotations(
            project=self.PROJECT_NAME,
            image_name=self.EXAMPLE_IMAGE_1,
            annotation_json=f"{self.folder_path}/{self.EXAMPLE_IMAGE_1}___objects.json",
        )
        annotations = sa.get_annotations(self.PROJECT_NAME, [self.EXAMPLE_IMAGE_1])[0]
        self.assertEqual(annotations['instances'][0]['type'], 'tag')
        self.assertEqual(annotations['instances'][0]['attributes'][0]['name'], '1')
        self.assertEqual(annotations['instances'][0]['attributes'][0]['groupName'], 'g1')


class TestVectorAnnotationsWithTagFolderUpload(BaseTestCase):
    PROJECT_NAME = "TestVectorAnnotationsWithTagFolderUpload"
    PROJECT_TYPE = "Vector"
    PROJECT_DESCRIPTION = "TestVectorAnnotationsWithTag"
    TEST_FOLDER_PTH = "data_set/sample_project_vector_with_tag"
    EXAMPLE_IMAGE_1 = "example_image_1.jpg"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PTH)

    @property
    def classes_json_path(self):
        return f"{self.folder_path}/classes/classes.json"

    @pytest.mark.flaky(reruns=2)
    def test_vector_annotations_with_tag_folder_upload(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.classes_json_path
        )
        sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path
        )
        annotations = sa.get_annotations(self.PROJECT_NAME, [self.EXAMPLE_IMAGE_1])[0]
        self.assertEqual(annotations['instances'][0]['type'], 'tag')
        self.assertEqual(annotations['instances'][0]['attributes'][0]['name'], '1')
        self.assertEqual(annotations['instances'][0]['attributes'][0]['groupName'], 'g1')


class TestVectorAnnotationsWithTagFolderUploadPreannotation(BaseTestCase):
    PROJECT_NAME = "PreTestVectorAnnotationsWithTagFolderUpload"
    PROJECT_TYPE = "Vector"
    PROJECT_DESCRIPTION = "TestVectorAnnotationsWithTag"
    TEST_FOLDER_PTH = "data_set/sample_project_vector_with_tag"
    EXAMPLE_IMAGE_1 = "example_image_1.jpg"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PTH)

    @property
    def classes_json_path(self):
        return f"{self.folder_path}/classes/classes.json"

    def test_vector_annotations_with_tag_folder_upload_preannotation(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.classes_json_path
        )
        uploaded_annotations, _, _ = sa.upload_preannotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path
        )
        self.assertEqual(len(uploaded_annotations), 1)


class TestPixelImages(BaseTestCase):
    PROJECT_NAME = "sample_project_pixel"
    PROJECT_TYPE = "Pixel"
    PROJECT_DESCRIPTION = "Example Project test pixel basic images"
    TEST_FOLDER_PTH = "data_set/sample_project_pixel"
    EXAMPLE_IMAGE_1 = "example_image_1.jpg"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PTH)

    @property
    def classes_json_path(self):
        return f"{self.folder_path}/classes/classes.json"

    def test_basic_images(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            sa.upload_images_from_folder_to_project(
                self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
            )
            sa.create_annotation_classes_from_classes_json(
                self.PROJECT_NAME, self.classes_json_path
            )
            image = sa.get_item_metadata(self.PROJECT_NAME, "example_image_1.jpg")
            del image['createdAt']
            del image['updatedAt']
            truth = {'name': 'example_image_1.jpg', 'annotation_status': 'InProgress',
                     'prediction_status': 'NotStarted', 'segmentation_status': 'NotStarted', 'approval_status': None,
                     'annotator_email': None, 'qa_email': None, 'entropy_value': None}

            assert all([truth[i] == image[i] for i in truth])

            sa.upload_image_annotations(
                project=self.PROJECT_NAME,
                image_name=self.EXAMPLE_IMAGE_1,
                annotation_json=f"{self.folder_path}/{self.EXAMPLE_IMAGE_1}___pixel.json",
            )
            downloaded = sa.download_image(
                project=self.PROJECT_NAME,
                image_name=self.EXAMPLE_IMAGE_1,
                local_dir_path=temp_dir,
                include_annotations=True,
            )
            self.assertNotEqual(downloaded[1], (None, None))
            self.assertGreater(len(downloaded[0]), 0)

            sa.download_image_annotations(
                self.PROJECT_NAME, self.EXAMPLE_IMAGE_1, temp_dir
            )
            self.assertEqual(len(list(Path(temp_dir).glob("*"))), 3)
