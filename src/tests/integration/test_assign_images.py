import os
from os.path import dirname

import src.lib.app.superannotate as sa
from src.tests.integration.base import BaseTestCase


class TestAnnotationClasses(BaseTestCase):
    PROJECT_NAME = "test_assign_images"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    TEST_FOLDER_NAME = "test_folder"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"
    EXAMPLE_IMAGE_1 = "example_image_1.jpg"
    EXAMPLE_IMAGE_2 = "example_image_2.jpg"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    def test_assign_images(self):
        email = sa.get_team_metadata()["users"][0]["email"]
        sa.share_project(self._project["name"], email, "QA")

        sa.upload_images_from_folder_to_project(
            project=self._project["name"], folder_path=self.folder_path
        )

        sa.assign_images(
            self._project["name"], [self.EXAMPLE_IMAGE_1, self.EXAMPLE_IMAGE_2], email
        )
        image_metadata = sa.get_image_metadata(
            self._project["name"], self.EXAMPLE_IMAGE_1
        )
        self.assertEqual(image_metadata["qa_id"], email)

        sa.unshare_project(self._project["name"], email)
        image_metadata = sa.get_image_metadata(
            self._project["name"], self.EXAMPLE_IMAGE_1
        )

        self.assertIsNone(image_metadata["qa_id"])
        self.assertIsNone(image_metadata["annotator_id"])

        sa.share_project(self._project["name"], email, "Annotator")

        sa.assign_images(
            self._project["name"], [self.EXAMPLE_IMAGE_1, self.EXAMPLE_IMAGE_2], email
        )

        image_metadata = sa.get_image_metadata(
            self._project["name"], self.EXAMPLE_IMAGE_1
        )

        self.assertEqual(image_metadata["annotator_id"], email)
        self.assertIsNone(image_metadata["qa_id"])

    def test_assign_images_folder(self):

        email = sa.get_team_metadata()["users"][0]["email"]

        sa.share_project(self.PROJECT_NAME, email, "QA")
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME)

        project_folder = self._project["name"] + "/" + self.TEST_FOLDER_NAME

        sa.upload_images_from_folder_to_project(project_folder, self.folder_path)

        sa.assign_images(
            project_folder, [self.EXAMPLE_IMAGE_1, self.EXAMPLE_IMAGE_2], email
        )

        im1_metadata = sa.get_image_metadata(project_folder, self.EXAMPLE_IMAGE_1)
        im2_metadata = sa.get_image_metadata(project_folder, self.EXAMPLE_IMAGE_2)

        self.assertEqual(im1_metadata["qa_id"], email)
        self.assertEqual(im2_metadata["qa_id"], email)

        sa.unshare_project(self.PROJECT_NAME, email)

        im1_metadata = sa.get_image_metadata(project_folder, self.EXAMPLE_IMAGE_1)
        im2_metadata = sa.get_image_metadata(project_folder, self.EXAMPLE_IMAGE_2)

        self.assertIsNone(im1_metadata["qa_id"])
        self.assertIsNone(im2_metadata["qa_id"])
        self.assertIsNone(im1_metadata["annotator_id"])
        self.assertIsNone(im2_metadata["annotator_id"])

        sa.share_project(self.PROJECT_NAME, email, "Annotator")

        sa.assign_images(
            project_folder, [self.EXAMPLE_IMAGE_1, self.EXAMPLE_IMAGE_2], email
        )

        im1_metadata = sa.get_image_metadata(project_folder, self.EXAMPLE_IMAGE_1)
        im2_metadata = sa.get_image_metadata(project_folder, self.EXAMPLE_IMAGE_2)

        self.assertEqual(im1_metadata["annotator_id"], email)
        self.assertEqual(im2_metadata["annotator_id"], email)
        self.assertIsNone(im1_metadata["qa_id"])
        self.assertIsNone(im2_metadata["qa_id"])

    def test_un_assign_images(self):

        email = sa.get_team_metadata()["users"][0]["email"]
        sa.share_project(self.PROJECT_NAME, email, "QA")
        sa.upload_images_from_folder_to_project(self.PROJECT_NAME, self.folder_path)
        sa.assign_images(
            self.PROJECT_NAME, [self.EXAMPLE_IMAGE_1, self.EXAMPLE_IMAGE_2], email
        )
        sa.unassign_images(
            self.PROJECT_NAME, [self.EXAMPLE_IMAGE_1, self.EXAMPLE_IMAGE_2],
        )

        im1_metadata = sa.get_image_metadata(self.PROJECT_NAME, "example_image_1.jpg")
        im2_metadata = sa.get_image_metadata(self.PROJECT_NAME, "example_image_2.jpg")

        self.assertIsNone(im1_metadata["qa_id"])
        self.assertIsNone(im2_metadata["qa_id"])

        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME)
        project = self.PROJECT_NAME + "/" + self.TEST_FOLDER_NAME

        sa.move_images(
            self.PROJECT_NAME, [self.EXAMPLE_IMAGE_1, self.EXAMPLE_IMAGE_2], project
        )
        sa.assign_images(project, [self.EXAMPLE_IMAGE_1, self.EXAMPLE_IMAGE_2], email)
        sa.unassign_images(
            project, ["example_image_1.jpg", "example_image_2.jpg"],
        )

        sa.search_images(project)
        im1_metadata = sa.get_image_metadata(project, self.EXAMPLE_IMAGE_1)

        im2_metadata = sa.get_image_metadata(project, self.EXAMPLE_IMAGE_2)

        self.assertIsNone(im1_metadata["qa_id"])
        self.assertIsNone(im2_metadata["qa_id"])

    def test_assign_folder(self):
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME)
        email = sa.get_team_metadata()["users"][0]["email"]
        sa.share_project(self.PROJECT_NAME, email, "QA")
        sa.assign_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME, [email])
        folders = sa.search_folders(
            self.PROJECT_NAME, self.TEST_FOLDER_NAME, return_metadata=True
        )
        self.assertGreater(len(folders[0]["folder_users"]), 0)

    def test_un_assign_folder(self):
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME)
        email = sa.get_team_metadata()["users"][0]["email"]
        sa.share_project(self.PROJECT_NAME, email, "QA")
        sa.assign_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME, [email])
        folders = sa.search_folders(
            self.PROJECT_NAME, folder_name=self.TEST_FOLDER_NAME, return_metadata=True
        )
        self.assertGreater(len(folders[0]["folder_users"]), 0)
        sa.unassign_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME)

        folders = sa.search_folders(
            self.PROJECT_NAME, self.TEST_FOLDER_NAME, return_metadata=True
        )
        self.assertEqual(len(folders[0]["folder_users"]), 0)

    def test_assign_folder_unverified_users(self):

        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME)
        email = "unverified_user@mail.com"
        try:
            sa.assign_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME, [email])
        except Exception:
            pass

        # assert "Skipping unverified_user@mail.com from assignees." in caplog.text

    def test_assign_images_unverified_user(self):
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME)
        project_folder = self.PROJECT_NAME + "/" + self.TEST_FOLDER_NAME
        sa.upload_images_from_folder_to_project(project_folder, self.folder_path)
        email = "unverified_user@email.com"
        try:
            sa.assign_images(
                project_folder, [self.EXAMPLE_IMAGE_1, self.EXAMPLE_IMAGE_2], email
            )
        except Exception:
            pass
