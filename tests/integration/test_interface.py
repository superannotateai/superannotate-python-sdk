import os
from os.path import dirname
import src.superannotate as sa
from src.superannotate.lib.app.exceptions import AppException
from tests.integration.base import BaseTestCase


class TestInterface(BaseTestCase):
    PROJECT_NAME = "Interface test"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_NAME = "folder"
    EXAMPLE_IMAGE_1 = "example_image_1.jpg"
    EXAMPLE_IMAGE_2 = "example_image_2.jpg"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    def test_get_project_default_image_quality_in_editor(self):
        sa.invite_contributor_to_team(2, 2)
        self.assertIsNotNone(sa.get_project_default_image_quality_in_editor(self.PROJECT_NAME))

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
        print(sa.search_folders(self.PROJECT_NAME))
        with self.assertRaises(AppException):
            sa.delete_folders(self.PROJECT_NAME, ["non-existing folder"])

    def test_get_project_metadata(self):
        metadata = sa.get_project_metadata(self.PROJECT_NAME)
        self.assertIsNotNone(metadata["id"])
        self.assertListEqual(metadata.get("contributors", []), [])
        metadata_with_users = sa.get_project_metadata(self.PROJECT_NAME, include_contributors=True)
        self.assertIsNotNone(metadata_with_users.get("contributors"))
