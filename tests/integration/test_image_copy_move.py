import os
from os.path import dirname
from pathlib import Path
import pytest

import src.superannotate as sa
from tests.integration.base import BaseTestCase


class TestImageCopy(BaseTestCase):
    PROJECT_NAME = "test image copy 1"
    SECOND_PROJECT_NAME = "test image copy 2"
    PROJECT_DESCRIPTION = "Desc"
    TEST_FOLDER = "new_folder"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    EXAMPLE_IMAGE = "example_image_1.jpg"

    def setUp(self, *args, **kwargs):
        self.tearDown()
        self._project = sa.create_project(
            self.PROJECT_NAME, self.PROJECT_DESCRIPTION, self.PROJECT_TYPE
        )
        self._second_project = sa.create_project(
            self.SECOND_PROJECT_NAME, self.PROJECT_DESCRIPTION, self.PROJECT_TYPE
        )

    def tearDown(self) -> None:
        for project_name in (self.PROJECT_NAME, self.SECOND_PROJECT_NAME):
            projects = sa.search_projects(project_name, return_metadata=True)
            for project in projects:
                sa.delete_project(project)

    @property
    def folder_path(self):
        return Path(
            Path(os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH))
        )

    def test_image_copy(self):

        sa.upload_image_to_project(
            self.PROJECT_NAME,
            f"{self.folder_path}/example_image_1.jpg",
            annotation_status="InProgress",
        )
        sa.upload_image_to_project(
            self.PROJECT_NAME,
            f"{self.folder_path}/example_image_2.jpg",
            annotation_status="InProgress",
        )

        images = sa.search_images(self.PROJECT_NAME)
        self.assertEqual(len(images), 2)
        image = images[0]
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER)
        sa.copy_image(
            self.PROJECT_NAME, image, f"{self.PROJECT_NAME}/{self.TEST_FOLDER}", copy_annotation_status=True
        )
        images = sa.search_images(f"{self.PROJECT_NAME}/{self.TEST_FOLDER}")
        self.assertEqual(len(images), 1)

        dest_project = sa.create_project(
            self.SECOND_PROJECT_NAME + "dif", "test", "Vector"
        )
        sa.copy_image(self.PROJECT_NAME, image, dest_project["name"])
        images = sa.search_images(dest_project["name"], image)
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0], image)

    def test_image_copy_to_other_project(self):
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER)
        sa.create_folder(self.SECOND_PROJECT_NAME, self.TEST_FOLDER)
        sa.upload_image_to_project(
            f"{self.SECOND_PROJECT_NAME}/{self.TEST_FOLDER}",
            f"{self.folder_path}/{self.EXAMPLE_IMAGE}",
            annotation_status="InProgress",
        )

        sa.copy_image(
            f"{self.SECOND_PROJECT_NAME}/{self.TEST_FOLDER}",
            self.EXAMPLE_IMAGE, f"{self.PROJECT_NAME}/{self.TEST_FOLDER}",
            copy_annotation_status=True
        )

    def test_multiple_image_copy(self):

        sa.upload_image_to_project(
            self.PROJECT_NAME,
            f"{self.folder_path}/example_image_1.jpg",
            annotation_status="InProgress",
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        sa.upload_image_annotations(
            self.PROJECT_NAME,
            "example_image_1.jpg",
            f"{self.folder_path}/example_image_1.jpg___objects.json",
        )
        sa.upload_image_to_project(
            self.PROJECT_NAME,
            f"{self.folder_path}/example_image_2.jpg",
            annotation_status="InProgress",
        )
        sa.pin_image(self.PROJECT_NAME, "example_image_1.jpg")
        images = sa.search_images(self.PROJECT_NAME)
        self.assertEqual(len(images), 2)
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER)
        sa.copy_image(
            self.PROJECT_NAME,
            "example_image_1.jpg",
            f"{self.PROJECT_NAME}/{self.TEST_FOLDER}",
            include_annotations=True,
            copy_annotation_status=True,
            copy_pin=True,
        )
        self.assertEqual(
            len(sa.search_images(f"{self.PROJECT_NAME}/{self.TEST_FOLDER}")), 1
        )
        annotations = sa.get_image_annotations(
            f"{self.PROJECT_NAME}/{self.TEST_FOLDER}", "example_image_1.jpg"
        )
        self.assertTrue(annotations["annotation_json"] is not None)

        metadata = sa.get_image_metadata(
            f"{self.PROJECT_NAME}/{self.TEST_FOLDER}", "example_image_1.jpg"
        )
        self.assertEqual(metadata["is_pinned"], 1)

    def test_image_move(self):
        sa.upload_image_to_project(
            self.PROJECT_NAME,
            f"{self.folder_path}/{self.EXAMPLE_IMAGE}",
            annotation_status="InProgress",
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        sa.upload_image_annotations(
            self.PROJECT_NAME,
            self.EXAMPLE_IMAGE,
            f"{self.folder_path}/{self.EXAMPLE_IMAGE}___objects.json",
        )
        sa.upload_image_to_project(
            self.PROJECT_NAME,
            f"{self.folder_path}/example_image_2.jpg",
            annotation_status="InProgress",
        )
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER)
        self.assertEqual(len(sa.search_images(self.PROJECT_NAME)), 2)
        with self.assertRaises(Exception):
            sa.move_image(self.PROJECT_NAME, self.EXAMPLE_IMAGE, self.PROJECT_NAME)

        sa.move_image(self.PROJECT_NAME, self.EXAMPLE_IMAGE, self.SECOND_PROJECT_NAME)
        di = sa.search_images(self.SECOND_PROJECT_NAME, self.EXAMPLE_IMAGE)
        self.assertEqual(len(di), 1)
        self.assertEqual(di[0], self.EXAMPLE_IMAGE)

        si = sa.search_images(self.PROJECT_NAME, self.EXAMPLE_IMAGE)
        self.assertEqual(len(si), 0)

        si = sa.search_images(self.PROJECT_NAME)
        self.assertEqual(len(si), 1)

    @pytest.mark.flaky(reruns=2)
    def test_copy_image_with_arguments(self):
        sa.upload_image_to_project(
            self.PROJECT_NAME,
            f"{self.folder_path}/{self.EXAMPLE_IMAGE}",
            annotation_status="InProgress",
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        sa.upload_image_annotations(
            self.PROJECT_NAME,
            self.EXAMPLE_IMAGE,
            f"{self.folder_path}/{self.EXAMPLE_IMAGE}___objects.json",
        )
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER)
        sa.copy_image(
            self.PROJECT_NAME, self.EXAMPLE_IMAGE, f"{self.PROJECT_NAME}/{self.TEST_FOLDER}",
            copy_annotation_status=True
        )

# def test_image_copy_folders(tmpdir):
#     tmpdir = Path(tmpdir)

#     projects_found = sa.search_projects(
#         PROJECT_NAME_FOLDER, return_metadata=True
#     )
#     for pr in projects_found:
#         sa.delete_project(pr)

#     project = sa.create_project(PROJECT_NAME_FOLDER, "test", "Vector")

#     sa.upload_image_to_project(
#         project,
#         "./tests/sample_project_vector/example_image_1.jpg",
#         annotation_status="InProgress"
#     )
#     sa.upload_image_to_project(
#         project,
#         "./tests/sample_project_vector/example_image_2.jpg",
#         annotation_status="InProgress"
#     )

#     sa.create_folder(project, "folder1")

#     sa.copy_image(
#         project, ["example_image_1.jpg", "example_image_2.jpg"],
#         project["name"] + "/folder1"
#     )
#     sa.copy_image(
#         project, ["example_image_1.jpg", "example_image_2.jpg"],
#         project["name"] + "/folder1"
#     )
