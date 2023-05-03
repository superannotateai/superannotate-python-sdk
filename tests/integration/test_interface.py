import os
import tempfile
from os.path import dirname

import pytest
from src.superannotate import AppException
from src.superannotate import export_annotation
from src.superannotate import SAClient
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestInterface(BaseTestCase):
    PROJECT_NAME = "Interface test"
    TEST_FOLDER_PATH = "sample_project_vector"
    TEST_FOLDER_PATH_WITH_MULTIPLE_IMAGERS = "data_set/sample_project_vector"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_NAME = "folder"
    EXAMPLE_IMAGE_1 = "example_image_1.jpg"
    EXAMPLE_IMAGE_2 = "example_image_2.jpg"
    NEW_IMAGE_NAME = "new_name_yup"
    TEST_INVALID_ANNOTATION_FOLDER_PATH = "sample_project_vector_invalid"

    @property
    def invalid_json_path(self):
        return os.path.join(
            self.data_set_path, self.TEST_INVALID_ANNOTATION_FOLDER_PATH
        )

    @property
    def data_set_path(self):
        return os.path.join(dirname(dirname(__file__)), "data_set")

    @property
    def folder_path(self):
        return os.path.join(self.data_set_path, self.TEST_FOLDER_PATH)

    @property
    def folder_path_with_multiple_images(self):
        return os.path.join(
            dirname(dirname(__file__)), self.TEST_FOLDER_PATH_WITH_MULTIPLE_IMAGERS
        )

    def test_download_image_annotations(self):
        sa.upload_images_from_folder_to_project(self.PROJECT_NAME, self.folder_path)
        with tempfile.TemporaryDirectory() as temp_dir:
            sa.download_image_annotations(
                self.PROJECT_NAME, self.EXAMPLE_IMAGE_1, temp_dir
            )

    def test_overlay_fuse(self):
        sa.upload_image_to_project(
            self.PROJECT_NAME, f"{self.folder_path}/{self.EXAMPLE_IMAGE_1}"
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        sa.upload_image_annotations(
            self.PROJECT_NAME,
            self.EXAMPLE_IMAGE_1,
            f"{self.folder_path}/{self.EXAMPLE_IMAGE_1}___objects.json",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = sa.download_image(
                self.PROJECT_NAME,
                self.EXAMPLE_IMAGE_1,
                temp_dir,
                include_annotations=True,
                include_fuse=True,
                include_overlay=True,
            )
            self.assertIsNotNone(paths)

    def test_download_fuse_without_classes(self):
        sa.upload_image_to_project(
            self.PROJECT_NAME, f"{self.folder_path}/{self.EXAMPLE_IMAGE_1}"
        )
        sa.upload_image_annotations(
            self.PROJECT_NAME,
            self.EXAMPLE_IMAGE_1,
            f"{self.folder_path}/{self.EXAMPLE_IMAGE_1}___objects.json",
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = sa.download_image(
                self.PROJECT_NAME,
                self.EXAMPLE_IMAGE_1,
                tmp_dir,
                include_annotations=True,
            )
            self.assertIsNotNone(result)


class TestPixelInterface(BaseTestCase):
    PROJECT_NAME = "Interface Pixel test"
    TEST_FOLDER_PATH = "sample_project_pixel"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Pixel"
    TEST_FOLDER_NAME = "folder"
    EXAMPLE_IMAGE_1 = "example_image_1.jpg"

    @property
    def data_set_path(self):
        return os.path.join(dirname(dirname(__file__)), "data_set")

    @property
    def folder_path(self):
        return os.path.join(self.data_set_path, self.TEST_FOLDER_PATH)

    @pytest.mark.flaky(reruns=2)
    def test_export_annotation(self):
        sa.upload_image_to_project(
            self.PROJECT_NAME, f"{self.folder_path}/{self.EXAMPLE_IMAGE_1}"
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        sa.upload_image_annotations(
            self.PROJECT_NAME,
            self.EXAMPLE_IMAGE_1,
            f"{self.folder_path}/{self.EXAMPLE_IMAGE_1}___pixel.json",
        )
        with tempfile.TemporaryDirectory() as export_dir:
            result = sa.prepare_export(
                self.PROJECT_NAME,
            )
            sa.download_export(self.PROJECT_NAME, result, export_dir, True)
            with tempfile.TemporaryDirectory() as convert_path:
                export_annotation(
                    export_dir,
                    convert_path,
                    "COCO",
                    "data_set_name",
                    "Pixel",
                    "panoptic_segmentation",
                )
                pass

    @pytest.mark.skip(reason="Need to adjust")
    def test_create_folder_with_special_character(self):
        with self.assertLogs() as logs:
            folder_1 = sa.create_folder(self.PROJECT_NAME, "**abc")
            folder_2 = sa.create_folder(self.PROJECT_NAME, "**abc")
            self.assertEqual(folder_1["name"], "__abc")
            self.assertEqual(folder_2["name"], "__abc (1)")
            self.assertIn(
                "New folder name has special characters. Special characters will be replaced by underscores.",
                logs.output[0],
            )
            self.assertIn(
                "Folder __abc created in project Interface Pixel test", logs.output[1]
            )
            self.assertIn(
                "New folder name has special characters. Special characters will be replaced by underscores.",
                logs.output[2],
            )
            self.assertIn(
                "Created folder has name __abc (1), since folder with name __abc already existed.",
                logs.output[3],
            )
            self.assertIn(
                "Folder __abc (1) created in project Interface Pixel test",
                logs.output[4],
            )
