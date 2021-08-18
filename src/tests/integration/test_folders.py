import os
import pathlib
import tempfile
import time
from os.path import dirname

import src.lib.app.superannotate as sa
from src.tests.integration.base import BaseTestCase


class TestFolders(BaseTestCase):
    PROJECT_NAME = "test folders"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_NAME_1 = "folder_1"
    TEST_FOLDER_NAME_2 = "folder_2"
    EXAMPLE_IMAGE_1 = "example_image_1"
    EXAMPLE_IMAGE_2 = "example_image_2"
    EXAMPLE_IMAGE_3 = "example_image_3.jpg"
    EXAMPLE_IMAGE_4 = "example_image_4.jpg"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    @property
    def classes_json(self):
        return f"{self.folder_path}/classes/classes.json"

    def test_basic_folders(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        images = sa.search_images(self.PROJECT_NAME, self.EXAMPLE_IMAGE_1)
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

        images = sa.search_images(
            self.PROJECT_NAME + f"/{self.TEST_FOLDER_NAME_1}", self.EXAMPLE_IMAGE_1
        )
        self.assertEqual(len(images), 0)

        images = sa.search_images_all_folders(self.PROJECT_NAME, self.EXAMPLE_IMAGE_1)
        self.assertEqual(len(images), 1)

        folder = sa.get_folder_metadata(self.PROJECT_NAME, self.TEST_FOLDER_NAME_1)
        self.assertIsInstance(folder, dict)
        self.assertEqual(folder["name"], self.TEST_FOLDER_NAME_1)

        # todo fix
        # with pytest.raises(EmptyOutputError) as exc_info:
        #     sa.get_folder_metadata(self.PROJECT_NAME, self.TEST_FOLDER_NAME_2)
        # self.assertTrue("Folder not found" in str(exc_info))

        sa.upload_images_from_folder_to_project(
            f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME_1}",
            self.folder_path,
            annotation_status="InProgress",
        )
        images = sa.search_images(
            f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME_1}", self.EXAMPLE_IMAGE_1
        )
        self.assertEqual(len(images), 1)

        sa.upload_images_from_folder_to_project(
            f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME_1}",
            self.folder_path,
            annotation_status="InProgress",
        )
        images = sa.search_images(f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME_1}")
        self.assertEqual(len(images), 4)

        # todo fix
        # with pytest.raises(AppException) as e:
        #     sa.upload_images_from_folder_to_project(
        #         f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME_1}",
        #         self.folder_path,
        #         annotation_status="InProgress",
        #     )
        # self.assertTrue("Folder not found" in str(e))

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
        annotations = sa.get_image_annotations(
            f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME_1}",
            f"{self.EXAMPLE_IMAGE_1}.jpg",
        )
        self.assertGreater(len(annotations["annotation_json"]["instances"]), 0)

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

    def test_rename_folder(self):
        sa.create_folder(self.PROJECT_NAME, "folder_1")
        sa.create_folder(self.PROJECT_NAME, "folder_2")
        sa.create_folder(self.PROJECT_NAME, "folder_3")
        self.assertEqual(len(sa.search_folders(self.PROJECT_NAME)), 3)

        sa.rename_folder(f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME_1}", "folder_5")
        self.assertEqual(len(sa.search_folders(self.PROJECT_NAME)), 3)

        self.assertTrue("folder_5" in sa.search_folders(self.PROJECT_NAME))
        self.assertTrue("folder_1" not in sa.search_folders(self.PROJECT_NAME))

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

    def test_delete_images(self):
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

        sa.delete_images(
            f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME_1}",
            ["example_image_2.jpg", "example_image_3.jpg"],
        )
        num_images = sa.get_project_image_count(
            self.PROJECT_NAME, with_all_subfolders=True
        )
        self.assertEqual(num_images, 2)

        sa.delete_images(self.PROJECT_NAME, None)
        time.sleep(2)
        num_images = sa.get_project_image_count(
            self.PROJECT_NAME, with_all_subfolders=False
        )
        self.assertEqual(num_images, 0)

    def test_copy_images3(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        sa.create_folder(f"{self.PROJECT_NAME}", self.TEST_FOLDER_NAME_1)
        sa.copy_images(
            f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME_1}",
            [self.EXAMPLE_IMAGE_2, self.EXAMPLE_IMAGE_3],
            f"{self.PROJECT_NAME}",
            include_annotations=False,
            copy_annotation_status=False,
            copy_pin=False,
        )
        assert (
            "Copied 2/2 images from test copy3 folder images to test copy3 folder images/folder_1"
            # todo add in caplog.text
        )

        num_images = sa.get_project_image_count(self.PROJECT_NAME)
        assert num_images == 4

    def test_copy_images4(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_1)
        project = f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME_1}"

        sa.copy_images(
            self.PROJECT_NAME, ["example_image_2.jpg", "example_image_3.jpg"], project
        )

        num_images = sa.get_project_image_count(project)
        self.assertEqual(num_images, 2)

        num_images = sa.get_project_image_count(self.PROJECT_NAME)
        self.assertEqual(num_images, 4)

    def test_copy_images(self):
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_1)
        project = f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME_1}"
        sa.upload_images_from_folder_to_project(
            project, self.folder_path, annotation_status="InProgress"
        )
        num_images = sa.get_project_image_count(project)
        self.assertEqual(num_images, 4)

        im1 = sa.get_image_metadata(project, "example_image_2.jpg")
        self.assertEqual(im1["annotation_status"], "InProgress")

        sa.create_folder(self.PROJECT_NAME, "folder2")
        project2 = self.PROJECT_NAME + "/folder2"
        num_images = sa.get_project_image_count(project2)
        self.assertEqual(num_images, 0)

        sa.copy_images(
            project,
            ["example_image_2.jpg", "example_image_3.jpg"],
            project2,
            include_annotations=False,
            copy_annotation_status=False,
            copy_pin=False,
        )

        im1_copied = sa.get_image_metadata(project2, "example_image_2.jpg")
        self.assertEqual(im1_copied["annotation_status"], "NotStarted")

        ann2 = sa.get_image_annotations(project2, "example_image_2.jpg")
        # todo check
        # self.assertEqual(len(ann2["annotation_json"]["instances"]), 0)

        num_images = sa.get_project_image_count(project2)
        self.assertEqual(num_images, 2)

        res = sa.copy_images(project, None, project2)

        num_images = sa.get_project_image_count(project2)
        self.assertEqual(num_images, 4)

        self.assertEqual(len(res), 2)

        sa.copy_images(
            project,
            ["example_image_2.jpg", "example_image_3.jpg"],
            self.PROJECT_NAME,
            include_annotations=False,
            copy_annotation_status=False,
            copy_pin=False,
        )
        num_images = sa.get_project_image_count(self.PROJECT_NAME)
        self.assertEqual(num_images, 2)

    def test_move_images(self):
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_1)
        project = f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME_1}"
        sa.upload_images_from_folder_to_project(
            project, self.folder_path, annotation_status="InProgress"
        )
        num_images = sa.get_project_image_count(project)
        self.assertEqual(num_images, 4)

        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_2)
        project2 = self.PROJECT_NAME + "/" + self.TEST_FOLDER_NAME_2
        num_images = sa.get_project_image_count(project2)
        self.assertEqual(num_images, 0)

        sa.move_images(project, ["example_image_2.jpg"], project2)
        num_images = sa.get_project_image_count(project2)
        self.assertEqual(num_images, 1)

        num_images = sa.get_project_image_count(project)
        self.assertEqual(num_images, 3)

        num_images = sa.get_project_image_count(
            self.PROJECT_NAME, with_all_subfolders=True
        )
        self.assertEqual(num_images, 4)

        images = sa.search_images_all_folders(self.PROJECT_NAME)
        self.assertEqual(
            images,
            [
                "example_image_1.jpg",
                "example_image_2.jpg",
                "example_image_3.jpg",
                "example_image_4.jpg",
            ],
        )

    def test_move_images2(self):
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_1)
        project = f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME_1}"
        sa.upload_images_from_folder_to_project(
            project, self.folder_path, annotation_status="InProgress"
        )
        num_images = sa.get_project_image_count(project)
        self.assertEqual(num_images, 4)

        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_2)
        project2 = self.PROJECT_NAME + "/" + self.TEST_FOLDER_NAME_2
        num_images = sa.get_project_image_count(project2)
        self.assertEqual(num_images, 0)

        sa.move_images(project, None, project2)
        num_images = sa.get_project_image_count(project2)
        self.assertEqual(num_images, 4)

        num_images = sa.get_project_image_count(project)
        self.assertEqual(num_images, 0)

    def test_copy_images2(self):
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.classes_json
        )
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_1)
        project = f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME_1}"
        sa.upload_images_from_folder_to_project(
            project, self.folder_path, annotation_status="InProgress"
        )
        sa.upload_annotations_from_folder_to_project(project, self.folder_path)
        num_images = sa.get_project_image_count(project)
        self.assertEqual(num_images, 4)

        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_2)
        project2 = f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME_2}"
        num_images = sa.get_project_image_count(project2)
        self.assertEqual(num_images, 0)

        sa.pin_image(project, "example_image_2.jpg")

        im1 = sa.get_image_metadata(project, "example_image_2.jpg")
        self.assertTrue(im1["is_pinned"])
        self.assertEqual(im1["annotation_status"], "InProgress")

        sa.copy_images(
            project, ["example_image_2.jpg", "example_image_3.jpg"], project2
        )

        num_images = sa.get_project_image_count(project2)
        self.assertEqual(num_images, 2)

        ann1 = sa.get_image_annotations(project, "example_image_2.jpg")
        ann2 = sa.get_image_annotations(project2, "example_image_2.jpg")
        self.assertEqual(ann1, ann2)

        im1_copied = sa.get_image_metadata(project2, "example_image_2.jpg")
        self.assertTrue(im1_copied["is_pinned"])
        self.assertEqual(im1_copied["annotation_status"], "InProgress")

        im2_copied = sa.get_image_metadata(project2, "example_image_3.jpg")
        self.assertFalse(im2_copied["is_pinned"])
        self.assertEqual(im2_copied["annotation_status"], "InProgress")

    def test_folder_export(self):

        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.classes_json
        )
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_1)
        project = f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME_1}"
        sa.upload_images_from_folder_to_project(
            project, self.folder_path, annotation_status="InProgress"
        )

        sa.upload_annotations_from_folder_to_project(project, self.folder_path)
        num_images = sa.get_project_image_count(project)
        self.assertEqual(num_images, 4)

        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_2)
        project2 = f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME_2}"
        num_images = sa.get_project_image_count(project2)
        self.assertEqual(num_images, 0)

        sa.copy_images(
            project, ["example_image_2.jpg", "example_image_3.jpg"], project2
        )

        export = sa.prepare_export(
            self.PROJECT_NAME, [self.TEST_FOLDER_NAME_2, self.TEST_FOLDER_NAME_1]
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = pathlib.Path(temp_dir)
            sa.download_export(project, export, temp_dir)
            self.assertEqual(len(list((temp_dir / "classes").rglob("*"))), 1)
            self.assertEqual(
                len(list((temp_dir / self.TEST_FOLDER_NAME_1).rglob("*"))), 4
            )
            self.assertEqual(
                len(list((temp_dir / self.TEST_FOLDER_NAME_2).rglob("*"))), 2
            )
            self.assertEqual(len(list((temp_dir).glob("*.*"))), 0)

            export = sa.prepare_export(self.PROJECT_NAME)
            sa.download_export(project, export, temp_dir)
            self.assertEqual(len(list((temp_dir / "classes").rglob("*"))), 1)
            self.assertEqual(
                len(list((temp_dir / self.TEST_FOLDER_NAME_1).rglob("*"))), 4
            )
            self.assertEqual(
                len(list((temp_dir / self.TEST_FOLDER_NAME_2).rglob("*"))), 2
            )
            self.assertEqual(len(list((temp_dir).glob("*.*"))), 4)

    def test_folder_image_annotation_status(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME_1)
        project = f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME_1}"
        sa.upload_images_from_folder_to_project(
            project, self.folder_path, annotation_status="InProgress"
        )
        sa.set_images_annotation_statuses(
            project, ["example_image_1.jpg", "example_image_2.jpg"], "QualityCheck"
        )
        for image in ["example_image_1.jpg", "example_image_2.jpg"]:
            metadata = sa.get_image_metadata(project, image)
            self.assertEqual(metadata["annotation_status"], "QualityCheck")

        for image in ["example_image_3.jpg", "example_image_3.jpg"]:
            metadata = sa.get_image_metadata(project, image)
            self.assertEqual(metadata["annotation_status"], "InProgress")

        sa.set_images_annotation_statuses(self.PROJECT_NAME, None, "QualityCheck")

        for image in sa.search_images(self.PROJECT_NAME):
            metadata = sa.get_image_metadata(self.PROJECT_NAME, image)
            self.assertEqual(metadata["annotation_status"], "QualityCheck")

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
