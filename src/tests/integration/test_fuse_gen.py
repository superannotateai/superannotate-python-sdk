import os
import pathlib
import tempfile
from os.path import dirname

import numpy as np
import src.lib.app.superannotate as sa
from PIL import Image
from src.tests.integration.base import BaseTestCase


class TestFolders(BaseTestCase):
    PROJECT_NAME = "test fuse"
    TEST_VECTOR_FOLDER_PATH = "data_set/sample_project_vector"
    TEST_PIXEL_FOLDER_PATH = "data_set/sample_project_pixel"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Pixel"
    TEST_FOLDER_NAME_1 = "folder_1"
    TEST_FOLDER_NAME_2 = "folder_2"
    EXAMPLE_IMAGE_1 = "example_image_1.jpg"
    EXAMPLE_IMAGE_2 = "example_image_2"

    @property
    def vector_folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_VECTOR_FOLDER_PATH)

    @property
    def pixel_folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_PIXEL_FOLDER_PATH)

    @property
    def vector_classes_json(self):
        return f"{self.vector_folder_path}/classes/classes.json"

    @property
    def pixel_classes_json(self):
        return f"{self.pixel_folder_path}/classes/classes.json"

    def test_fuse_image_create_vector(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = pathlib.Path(temp_dir)

            sa.upload_image_to_project(
                self.PROJECT_NAME,
                f"{self.vector_folder_path}/{self.EXAMPLE_IMAGE_1}",
                annotation_status="QualityCheck",
            )

            sa.create_annotation_classes_from_classes_json(
                self.PROJECT_NAME, self.vector_classes_json
            )

            sa.add_annotation_bbox_to_image(
                self.PROJECT_NAME, self.EXAMPLE_IMAGE_1, [20, 20, 40, 40], "Human"
            )
            sa.add_annotation_polygon_to_image(
                self.PROJECT_NAME,
                self.EXAMPLE_IMAGE_1,
                [60, 60, 100, 100, 80, 100],
                "Personal vehicle",
            )
            sa.add_annotation_polyline_to_image(
                self.PROJECT_NAME,
                self.EXAMPLE_IMAGE_1,
                [200, 200, 300, 200, 350, 300],
                "Personal vehicle",
            )
            sa.add_annotation_point_to_image(
                self.PROJECT_NAME, self.EXAMPLE_IMAGE_1, [400, 400], "Personal vehicle"
            )
            sa.add_annotation_ellipse_to_image(
                self.PROJECT_NAME,
                self.EXAMPLE_IMAGE_1,
                [600, 600, 50, 100, 20],
                "Personal vehicle",
            )
            sa.add_annotation_template_to_image(
                self.PROJECT_NAME,
                self.EXAMPLE_IMAGE_1,
                [600, 300, 600, 350, 550, 250, 650, 250, 550, 400, 650, 400],
                [1, 2, 3, 1, 4, 1, 5, 2, 6, 2],
                "Human",
            )
            sa.add_annotation_cuboid_to_image(
                self.PROJECT_NAME,
                self.EXAMPLE_IMAGE_1,
                [60, 300, 200, 350, 120, 325, 250, 500],
                "Human",
            )

            export = sa.prepare_export(self.PROJECT_NAME, include_fuse=True)
            (temp_dir / "export").mkdir()
            sa.download_export(self.PROJECT_NAME, export, (temp_dir / "export"))

            # sa.create_fuse_image(
            #     "./tests/sample_project_vector/example_image_1.jpg",
            #     "./tests/sample_project_vector/classes/classes.json", "Vector"
            # )

            paths = sa.download_image(
                self.PROJECT_NAME,
                self.EXAMPLE_IMAGE_1,
                temp_dir,
                include_annotations=True,
                include_fuse=True,
                include_overlay=True,
            )
            im1 = Image.open(temp_dir / "export" / f"{self.EXAMPLE_IMAGE_1}___fuse.png")
            im1_array = np.array(im1)

            im2 = Image.open(paths[2][0])
            im2_array = np.array(im2)

            self.assertEqual(im1_array.shape, im2_array.shape)
            self.assertEqual(im1_array.dtype, im2_array.dtype)

    def test_fuse_image_create_pixel(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = pathlib.Path(temp_dir)

            projects = sa.search_projects(self.PROJECT_NAME, return_metadata=True)
            for project in projects:
                sa.delete_project(project)
            sa.create_project(self.PROJECT_NAME, "test", "Pixel")

            sa.upload_image_to_project(
                self.PROJECT_NAME,
                f"{self.vector_folder_path}/{self.EXAMPLE_IMAGE_1}",
                annotation_status="QualityCheck",
            )

            sa.create_annotation_classes_from_classes_json(
                self.PROJECT_NAME, self.pixel_classes_json
            )
            sa.upload_image_annotations(
                self.PROJECT_NAME,
                self.EXAMPLE_IMAGE_1,
                f"{self.pixel_folder_path}/{self.EXAMPLE_IMAGE_1}___pixel.json",
                f"{self.pixel_folder_path}/{self.EXAMPLE_IMAGE_1}___save.png",
            )

            export = sa.prepare_export(self.PROJECT_NAME, include_fuse=True)["name"]
            (temp_dir / "export").mkdir()
            sa.download_export(self.PROJECT_NAME, export, (temp_dir / "export"))

            sa.create_fuse_image(
                f"{self.vector_folder_path}/{self.EXAMPLE_IMAGE_1}",
                f"{self.vector_folder_path}/classes/classes.json",
                "Vector",
            )

            paths = sa.download_image(
                self.PROJECT_NAME,
                self.EXAMPLE_IMAGE_1,
                temp_dir,
                include_annotations=True,
                include_fuse=True,
            )
            print(paths, paths[2])
            im1 = Image.open(temp_dir / "export" / f"{self.EXAMPLE_IMAGE_1}___fuse.png")
            im1_array = np.array(im1)

            im2 = Image.open(paths[2][0])
            im2_array = np.array(im2)

            self.assertEqual(im1_array.shape, im2_array.shape)
            self.assertEqual(im1_array.dtype, im2_array.dtype)
            self.assertTrue(np.array_equal(im1_array, im2_array))
