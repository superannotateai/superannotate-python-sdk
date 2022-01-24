import os
from os.path import dirname
import tempfile
import pytest

import src.superannotate as sa
from src.superannotate.lib.app.exceptions import AppException
from tests.integration.base import BaseTestCase


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
    IMAGE_PATH_IN_S3 = 'MP.MB/img1.bmp'
    TEST_S3_BUCKET_NAME = "test-openseadragon-1212"

    @property
    def data_set_path(self):
        return os.path.join(dirname(dirname(__file__)), "data_set")

    @property
    def folder_path(self):
        return os.path.join(self.data_set_path, self.TEST_FOLDER_PATH)

    @property
    def folder_path_with_multiple_images(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH_WITH_MULTIPLE_IMAGERS)

    @pytest.mark.flaky(reruns=2)
    def test_delete_images(self):
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME)

        sa.upload_images_from_folder_to_project(
            f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME}",
            self.folder_path,
            annotation_status="InProgress",
        )
        num_images = sa.get_project_image_count(
            self.PROJECT_NAME, with_all_subfolders=True
        )
        self.assertEqual(num_images, 4)
        sa.delete_images(f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME}")

        num_images = sa.get_project_image_count(
            self.PROJECT_NAME, with_all_subfolders=True
        )
        self.assertEqual(num_images, 0)

    def test_delete_folder(self):
        with self.assertRaises(AppException):
            sa.delete_folders(self.PROJECT_NAME, ["non-existing folder"])

    def test_get_project_metadata(self):
        metadata = sa.get_project_metadata(self.PROJECT_NAME)
        self.assertIsNotNone(metadata["id"])
        self.assertListEqual(metadata.get("contributors", []), [])
        metadata_with_users = sa.get_project_metadata(self.PROJECT_NAME, include_contributors=True)
        self.assertIsNotNone(metadata_with_users.get("contributors"))

    def test_upload_annotations_from_folder_to_project(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME,
            self.folder_path,
            annotation_status="Completed",
        )
        uploaded_annotations, _, _ = sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path
        )
        self.assertEqual(len(uploaded_annotations), 4)

    def test_download_image_annotations(self):
        sa.upload_images_from_folder_to_project(self.PROJECT_NAME, self.folder_path)
        with tempfile.TemporaryDirectory() as temp_dir:
            sa.download_image_annotations(self.PROJECT_NAME, self.EXAMPLE_IMAGE_1, temp_dir)

    def test_search_folder(self):
        team_users = sa.search_team_contributors()
        sa.share_project(self.PROJECT_NAME, team_users[0], "QA")
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME)
        data = sa.search_folders(self.PROJECT_NAME, return_metadata=True)
        folder_data = sa.search_folders(self.PROJECT_NAME, self.TEST_FOLDER_NAME, return_metadata=True)
        self.assertEqual(data, folder_data)

    def test_search_project(self):
        sa.upload_images_from_folder_to_project(self.PROJECT_NAME, self.folder_path)
        sa.set_image_annotation_status(self.PROJECT_NAME, self.EXAMPLE_IMAGE_1, "Completed")
        data = sa.search_projects(self.PROJECT_NAME, return_metadata=True, include_complete_image_count=True)
        self.assertIsNotNone(data[0]['completed_images_count'])

    def test_overlay_fuse(self):
        sa.upload_image_to_project(self.PROJECT_NAME, f"{self.folder_path}/{self.EXAMPLE_IMAGE_1}")
        sa.create_annotation_classes_from_classes_json(self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json")
        sa.upload_image_annotations(
            self.PROJECT_NAME, self.EXAMPLE_IMAGE_1, f"{self.folder_path}/{self.EXAMPLE_IMAGE_1}___objects.json"
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

    def test_upload_images_to_project_returned_data(self):
        upload, not_uploaded, duplicated = sa.upload_images_to_project(
            self.PROJECT_NAME,
            [f"{self.folder_path}/{self.EXAMPLE_IMAGE_1}", f"{self.folder_path}/{self.EXAMPLE_IMAGE_2}"]
        )
        self.assertEqual(2, len(upload))
        upload, not_uploaded, duplicated = sa.upload_images_to_project(
            self.PROJECT_NAME,
            [f"{self.folder_path}/{self.EXAMPLE_IMAGE_1}", f"{self.folder_path}/{self.EXAMPLE_IMAGE_2}"]
        )
        self.assertEqual(2, len(duplicated))

    def test_upload_images_to_project_image_quality_in_editor(self):
        self.assertRaises(
            Exception,
            sa.upload_images_to_project,
            self.PROJECT_NAME,
            [self.EXAMPLE_IMAGE_1],
            image_quality_in_editor='random_string'
        )

    @pytest.mark.flaky(reruns=2)
    def test_image_upload_with_set_name_on_platform(self):
        sa.upload_image_to_project(
            self.PROJECT_NAME,
            self.IMAGE_PATH_IN_S3,
            self.NEW_IMAGE_NAME, from_s3_bucket=self.TEST_S3_BUCKET_NAME
        )
        self.assertIn(sa.search_images(self.PROJECT_NAME)[0], self.NEW_IMAGE_NAME)

    def test_download_fuse_without_classes(self):
        sa.upload_image_to_project(self.PROJECT_NAME, f"{self.folder_path}/{self.EXAMPLE_IMAGE_1}")
        sa.upload_image_annotations(
            self.PROJECT_NAME, self.EXAMPLE_IMAGE_1, f"{self.folder_path}/{self.EXAMPLE_IMAGE_1}___objects.json"
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = sa.download_image(
                self.PROJECT_NAME,
                self.EXAMPLE_IMAGE_1,
                tmp_dir,
                include_annotations=True,
                include_fuse=True
            )
            self.assertIsNotNone(result)

    def test_validate_log_for_single_uplaod(self):
        with self.assertLogs() as logs:
            sa.upload_image_to_project(self.PROJECT_NAME, f"{self.folder_path}/{self.EXAMPLE_IMAGE_1}")
            sa.upload_image_annotations(
                self.PROJECT_NAME, self.EXAMPLE_IMAGE_1, {
                    "metadatas": {
                        "name": "example_image_1.jpg",
                        "width": 1024,
                        "height": 683,
                        "status": "Completed",
                    },
                    "instance": []
                }
            )
            self.assertEqual(len(logs[1][0]), 150)



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
        sa.upload_image_to_project(self.PROJECT_NAME, f"{self.folder_path}/{self.EXAMPLE_IMAGE_1}")
        sa.create_annotation_classes_from_classes_json(self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json")
        sa.upload_image_annotations(
            self.PROJECT_NAME, self.EXAMPLE_IMAGE_1, f"{self.folder_path}/{self.EXAMPLE_IMAGE_1}___pixel.json"
        )
        with tempfile.TemporaryDirectory() as export_dir:
            result = sa.prepare_export(
                self.PROJECT_NAME,
            )
            sa.download_export(self.PROJECT_NAME, result, export_dir, True)
            with tempfile.TemporaryDirectory() as convert_path:
                sa.export_annotation(
                    export_dir, convert_path, "COCO", "data_set_name", "Pixel", "panoptic_segmentation"
                )
                pass

    def test_create_folder_with_special_character(self):
        with self.assertLogs() as logs:
            folder_1 = sa.create_folder(self.PROJECT_NAME, "**abc")
            folder_2 = sa.create_folder(self.PROJECT_NAME, "**abc")
            self.assertEqual(folder_1["name"], "__abc")
            self.assertEqual(folder_2["name"], "__abc (1)")
            self.assertIn(
                'New folder name has special characters. Special characters will be replaced by underscores.',
                logs.output[0]
            )
            self.assertIn(
                'Folder __abc created in project Interface Pixel test',
                logs.output[1]
            )
            self.assertIn(
                'New folder name has special characters. Special characters will be replaced by underscores.',
                logs.output[2]
            )
            self.assertIn(
                'Created folder has name __abc (1), since folder with name __abc already existed.',
                logs.output[3]
            )
            self.assertIn(
                'Folder __abc (1) created in project Interface Pixel test',
                logs.output[4]
            )
