import os
import tempfile
from os.path import dirname

import pytest

from src.superannotate import AppException
from src.superannotate import SAClient
from src.superannotate import export_annotation
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
    IMAGE_PATH_IN_S3 = 'MP.MB/img1.bmp'
    TEST_S3_BUCKET_NAME = "test-openseadragon-1212"
    TEST_INVALID_ANNOTATION_FOLDER_PATH = "sample_project_vector_invalid"

    @property
    def invalid_json_path(self):
        return os.path.join(self.data_set_path, self.TEST_INVALID_ANNOTATION_FOLDER_PATH)

    @property
    def data_set_path(self):
        return os.path.join(dirname(dirname(__file__)), "data_set")

    @property
    def folder_path(self):
        return os.path.join(self.data_set_path, self.TEST_FOLDER_PATH)

    @property
    def folder_path_with_multiple_images(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH_WITH_MULTIPLE_IMAGERS)

    @pytest.mark.flaky(reruns=4)
    def test_delete_items(self):
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME)

        path = f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME}"
        sa.upload_images_from_folder_to_project(
            path,
            self.folder_path,
            annotation_status="InProgress",
        )
        num_images = sa.get_project_image_count(
            self.PROJECT_NAME, with_all_subfolders=True
        )
        self.assertEqual(num_images, 4)
        sa.delete_items(path)

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
        sa.create_annotation_class(self.PROJECT_NAME, "tt", "#FFFFFF", class_type="tag")
        metadata_with_users = sa.get_project_metadata(self.PROJECT_NAME, include_annotation_classes=True,
                                                      include_contributors=True)
        self.assertEqual(metadata_with_users['classes'][0]['type'], 'tag')
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

    def test_search_project(self):
        sa.upload_images_from_folder_to_project(self.PROJECT_NAME, self.folder_path)
        sa.set_annotation_statuses(self.PROJECT_NAME,  "Completed", [self.EXAMPLE_IMAGE_1])
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
        assert self.NEW_IMAGE_NAME in [i["name"] for i in sa.search_items(self.PROJECT_NAME)]

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
            )
            self.assertIsNotNone(result)

    def test_validate_log_for_single_upload(self):
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

            sa.upload_image_annotations(
                self.PROJECT_NAME, self.EXAMPLE_IMAGE_1, {
                    "metadata": {
                        "name": "example_image_1.jpg",
                        "width": 1024,
                        "height": 683,
                        "status": "Completed",
                    },
                    "instance": []
                }
            )
            self.assertEqual(len(logs[1][1]), 86)

            sa.upload_images_from_folder_to_project(
                self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
            )
            uploaded_annotations, failed_annotations, missing_annotations = sa.upload_annotations_from_folder_to_project(
                self.PROJECT_NAME, self.invalid_json_path
            )
            self.assertEqual(len(uploaded_annotations), 3)
            self.assertEqual(len(failed_annotations), 1)
            self.assertEqual(len(missing_annotations), 0)
            self.assertEqual(len(logs[1][2].split("from")[0]), 98)
            self.assertEqual(len(logs[1][3]), 66)
            self.assertEqual(len(logs[1][4]), 53)
            self.assertEqual(len(logs[1][5]), 160)
            self.assertEqual(len(logs[1][6].split("from")[0]), 32)

            uploaded_annotations, failed_annotations, missing_annotations = sa.upload_preannotations_from_folder_to_project(
                self.PROJECT_NAME, self.invalid_json_path
            )
            self.assertEqual(len(uploaded_annotations), 3)
            self.assertEqual(len(failed_annotations), 1)
            self.assertEqual(len(missing_annotations), 0)

            with tempfile.TemporaryDirectory() as tmpdir_name:
                path = f"{tmpdir_name}/annotation___objects.json"
                with open(path, "w") as annotation:
                    annotation.write(
                        '''
                                           {
                                               "metadata": {
                                                   "name": "text_file_example_1",
                                                   "status": "NotStarted",
                                                   "url": "https://sa-public-files.s3.us-west-2.amazonaws.com/Text+project/text_file_example_1.txt",
                                                   "projectId": 167826,
                                                   "annotatorEmail": null,
                                                   "qaEmail": null,
                                                   "lastAction": {
                                                       "email": "some.email@gmail.com",
                                                       "timestamp": 1636620976450
                                                   }
                                               },
                                               "instances": [],
                                               "tags": []
                                           }
                                           '''
                    )
                sa.upload_image_annotations(self.PROJECT_NAME, self.EXAMPLE_IMAGE_1, path)
                self.assertEqual(len(logs[1][-1]), 86)
                self.assertEqual(len(logs[1][-2].split('from')[0]), 30)


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
                export_annotation(
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
