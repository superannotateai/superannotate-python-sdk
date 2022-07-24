import os
import pathlib
import tempfile
import time
from os.path import dirname

from src.superannotate import SAClient
sa = SAClient()
from tests.integration.base import BaseTestCase
from tests import DATA_SET_PATH

import pytest


class TestFolders(BaseTestCase):
    PROJECT_NAME = "test folders"
    TEST_FOLDER_PATH = "sample_project_vector"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"
    SPECIAL_CHARS = "/\:*?“<>|"
    TEST_FOLDER_NAME_1 = "folder_1"
    TEST_FOLDER_NAME_2 = "folder_2"
    EXAMPLE_IMAGE_1_NAME = "example_image_1"
    EXAMPLE_IMAGE_2_NAME = "example_image_2"
    EXAMPLE_IMAGE_1 = "example_image_1.jpg"
    EXAMPLE_IMAGE_2 = "example_image_2.jpg"
    EXAMPLE_IMAGE_3 = "example_image_3.jpg"
    EXAMPLE_IMAGE_4 = "example_image_4.jpg"

    @property
    def folder_path(self):
        return os.path.join(DATA_SET_PATH, self.TEST_FOLDER_PATH)

    @property
    def classes_json(self):
        return f"{self.folder_path}/classes/classes.json"

    def test_get_folder_metadata(self):
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_1)
        folder_metadata = sa.get_folder_metadata(self.PROJECT_NAME, self.TEST_FOLDER_NAME_1)
        assert "is_root" not in folder_metadata

    def test_search_folders(self):
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_1)
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_2)
        folders = sa.search_folders(self.PROJECT_NAME, return_metadata=True)
        assert all(["is_root" not in folder for folder in folders])

    def test_basic_folders(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        images = sa.search_items(self.PROJECT_NAME, self.EXAMPLE_IMAGE_1)
        self.assertEqual(len(images), 1)

        folders = sa.search_folders(self.PROJECT_NAME)
        self.assertEqual(len(folders), 0)

        folder_metadata = sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_1)
        self.assertEqual(folder_metadata["name"], self.TEST_FOLDER_NAME_1)

        folders = sa.search_folders(self.PROJECT_NAME, return_metadata=True)
        self.assertEqual(len(folders), 1)

        self.assertEqual(folders[0]["name"], self.TEST_FOLDER_NAME_1)

        folders = sa.search_folders(self.PROJECT_NAME)
        self.assertEqual(len(folders), 1)

        self.assertEqual(folders[0], self.TEST_FOLDER_NAME_1)

        images = sa.search_items(
            self.PROJECT_NAME + f"/{self.TEST_FOLDER_NAME_1}", self.EXAMPLE_IMAGE_1
        )
        self.assertEqual(len(images), 0)

        images = sa.search_items(self.PROJECT_NAME, self.EXAMPLE_IMAGE_1)
        self.assertEqual(len(images), 1)

        folder = sa.get_folder_metadata(self.PROJECT_NAME, self.TEST_FOLDER_NAME_1)
        self.assertIsInstance(folder, dict)
        self.assertEqual(folder["name"], self.TEST_FOLDER_NAME_1)

        with self.assertRaisesRegexp(Exception, "Folder not found"):
            sa.get_folder_metadata(self.PROJECT_NAME, self.TEST_FOLDER_NAME_2)

        sa.upload_images_from_folder_to_project(
            f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME_1}",
            self.folder_path,
            annotation_status="InProgress",
        )
        images = sa.search_items(
            f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME_1}", self.EXAMPLE_IMAGE_1
        )
        self.assertEqual(len(images), 1)

        sa.upload_images_from_folder_to_project(
            f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME_1}",
            self.folder_path,
            annotation_status="InProgress",
        )
        images = sa.search_items(f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME_1}")
        self.assertEqual(len(images), 4)

        folder_metadata = sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_2)
        self.assertEqual(folder_metadata["name"], self.TEST_FOLDER_NAME_2)

        folders = sa.search_folders(self.PROJECT_NAME)
        self.assertEqual(len(folders), 2)

        folders = sa.search_folders(self.PROJECT_NAME, folder_name="folder")
        self.assertEqual(len(folders), 2)

        folders = sa.search_folders(
            self.PROJECT_NAME, folder_name=self.TEST_FOLDER_NAME_2
        )
        self.assertEqual(len(folders), 1)
        self.assertEqual(folders[0], self.TEST_FOLDER_NAME_2)

        folders = sa.search_folders(
            self.PROJECT_NAME, folder_name=self.TEST_FOLDER_NAME_1
        )
        self.assertEqual(len(folders), 1)
        self.assertEqual(folders[0], self.TEST_FOLDER_NAME_1)

        folders = sa.search_folders(self.PROJECT_NAME, folder_name="old")
        self.assertEqual(len(folders), 2)

    def test_folder_annotations(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.classes_json
        )
        folder_metadata = sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_1)
        self.assertEqual(folder_metadata["name"], self.TEST_FOLDER_NAME_1)
        folders = sa.search_folders(self.PROJECT_NAME, return_metadata=True)
        self.assertEqual(len(folders), 1)

        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME + "/" + folders[0]["name"],
            self.folder_path,
            annotation_status="InProgress",
        )
        sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME + "/" + folders[0]["name"], self.folder_path
        )
        annotations = sa.get_annotations(f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME_1}", [self.EXAMPLE_IMAGE_1],)
        self.assertGreater(len(annotations[0]["instances"]), 0)

    def test_delete_folders(self):

        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_1)
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_2)

        self.assertEqual(len(sa.search_folders(self.PROJECT_NAME)), 2)

        sa.delete_folders(self.PROJECT_NAME, [self.TEST_FOLDER_NAME_1])
        self.assertEqual(len(sa.search_folders(self.PROJECT_NAME)), 1)
        sa.delete_folders(self.PROJECT_NAME, [self.TEST_FOLDER_NAME_2])
        self.assertEqual(len(sa.search_folders(self.PROJECT_NAME)), 0)
        sa.create_folder(self.PROJECT_NAME, "folder5")
        sa.create_folder(self.PROJECT_NAME, "folder6")
        self.assertEqual(len(sa.search_folders(self.PROJECT_NAME)), 2)

        sa.delete_folders(self.PROJECT_NAME, ["folder2", "folder5"])
        self.assertEqual(len(sa.search_folders(self.PROJECT_NAME)), 1)
        self.assertEqual(sa.search_folders(self.PROJECT_NAME)[0], "folder6")

    def test_project_folder_image_count(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        num_images = sa.get_project_image_count(self.PROJECT_NAME)
        self.assertEqual(num_images, 4)

        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_1)
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME + f"/{self.TEST_FOLDER_NAME_1}",
            self.folder_path,
            annotation_status="InProgress",
        )
        num_images = sa.get_project_image_count(self.PROJECT_NAME)
        self.assertEqual(num_images, 4)

        num_images = sa.get_project_image_count(
            self.PROJECT_NAME + f"/{self.TEST_FOLDER_NAME_1}"
        )
        self.assertEqual(num_images, 4)

        num_images = sa.get_project_image_count(
            self.PROJECT_NAME, with_all_subfolders=True
        )
        self.assertEqual(num_images, 8)

    def test_delete_items(self):
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_1)

        sa.upload_images_from_folder_to_project(
            f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME_1}",
            self.folder_path,
            annotation_status="InProgress",
        )
        num_images = sa.get_project_image_count(
            self.PROJECT_NAME, with_all_subfolders=True
        )
        self.assertEqual(num_images, 4)

        sa.delete_items(
            f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME_1}",
            [self.EXAMPLE_IMAGE_2, self.EXAMPLE_IMAGE_3],
        )
        num_images = sa.get_project_image_count(
            self.PROJECT_NAME, with_all_subfolders=True
        )
        self.assertEqual(num_images, 2)

        sa.delete_items(self.PROJECT_NAME, None)
        time.sleep(2)
        num_images = sa.get_project_image_count(
            self.PROJECT_NAME, with_all_subfolders=False
        )
        self.assertEqual(num_images, 0)

    @pytest.mark.flaky(reruns=2)
    def test_project_completed_count(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="Completed"
        )
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_1)
        project = f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME_1}"
        sa.upload_images_from_folder_to_project(
            project, self.folder_path, annotation_status="Completed"
        )
        project_metadata = sa.get_project_metadata(self.PROJECT_NAME, include_complete_image_count=True)
        self.assertEqual(project_metadata['completed_images_count'], 8)
        self.assertEqual(project_metadata['root_folder_completed_images_count'], 4)



    def test_folder_misnamed(self):

        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_1)
        self.assertTrue(self.TEST_FOLDER_NAME_1 in sa.search_folders(self.PROJECT_NAME))

        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_1)
        self.assertTrue(
            f"{self.TEST_FOLDER_NAME_1} (1)" in sa.search_folders(self.PROJECT_NAME)
        )

        sa.create_folder(self.PROJECT_NAME, f"{self.TEST_FOLDER_NAME_2}\\")
        self.assertTrue(
            f"{self.TEST_FOLDER_NAME_2}_" in sa.search_folders(self.PROJECT_NAME)
        )

    def test_create_folder_with_special_chars(self):
        sa.create_folder(self.PROJECT_NAME, self.SPECIAL_CHARS)
        folder = sa.get_folder_metadata(self.PROJECT_NAME, "_"*len(self.SPECIAL_CHARS))
        self.assertIsNotNone(folder)
