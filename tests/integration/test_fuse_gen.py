import os
import pathlib
import tempfile
from os.path import dirname
from unittest import TestCase
import pytest
import numpy as np
from src.superannotate import SAClient
sa = SAClient()
from PIL import Image


class TestFolders(TestCase):
    VECTOR_PROJECT_NAME = "vector test fuse"
    PIXEL_PROJECT_NAME = "pixel test fuse"
    PIXEL_PROJECT_NAME_FOR_FUSE = "pixel test fuse 1"
    TEST_VECTOR_FOLDER_PATH = "data_set/sample_project_vector"
    TEST_PIXEL_FOLDER_PATH = "data_set/sample_project_pixel"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Pixel"
    TEST_FOLDER_NAME_1 = "folder_1"
    TEST_FOLDER_NAME_2 = "folder_2"
    EXAMPLE_IMAGE_1 = "example_image_1.jpg"
    EXAMPLE_IMAGE_2 = "example_image_2"

    @classmethod
    def setUpClass(cls):
        cls.tearDownClass()
        cls._vector_project = sa.create_project(
            cls.VECTOR_PROJECT_NAME, cls.PROJECT_DESCRIPTION, "Vector"
        )
        cls._pixel_project = sa.create_project(
            cls.PIXEL_PROJECT_NAME, cls.PROJECT_DESCRIPTION, "Pixel"
        )

        cls._pixel_project_2 = sa.create_project(
            cls.PIXEL_PROJECT_NAME_FOR_FUSE, cls.PROJECT_DESCRIPTION, "Pixel"
        )

    @classmethod
    def tearDownClass(cls) -> None:
        projects = sa.search_projects(
            cls.VECTOR_PROJECT_NAME, return_metadata=True
        ) + sa.search_projects(cls.PIXEL_PROJECT_NAME, return_metadata=True) + \
                   sa.search_projects(cls.PIXEL_PROJECT_NAME_FOR_FUSE,return_metadata=True)
        for project in projects:
            sa.delete_project(project)

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

    @pytest.mark.flaky(reruns=3)
    def test_fuse_image_create_vector(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = pathlib.Path(temp_dir)

            sa.upload_image_to_project(
                self.VECTOR_PROJECT_NAME,
                f"{self.vector_folder_path}/{self.EXAMPLE_IMAGE_1}",
                annotation_status="QualityCheck",
            )

            sa.create_annotation_classes_from_classes_json(
                self.VECTOR_PROJECT_NAME, self.vector_classes_json
            )
            sa.upload_image_annotations(
                project=self.VECTOR_PROJECT_NAME,
                image_name=self.EXAMPLE_IMAGE_1,
                annotation_json=f"{self.vector_folder_path}/{self.EXAMPLE_IMAGE_1}___objects.json",
            )

            sa.add_annotation_bbox_to_image(
                self.VECTOR_PROJECT_NAME,
                self.EXAMPLE_IMAGE_1,
                [20, 20, 40, 40],
                "Human",
            )
            sa.add_annotation_point_to_image(
                self.VECTOR_PROJECT_NAME,
                self.EXAMPLE_IMAGE_1,
                [400, 400],
                "Personal vehicle",
            )
            export = sa.prepare_export(self.VECTOR_PROJECT_NAME, include_fuse=True)
            (temp_dir / "export").mkdir()
            sa.download_export(self.VECTOR_PROJECT_NAME, export, (temp_dir / "export"))

            paths = sa.download_image(
                self.VECTOR_PROJECT_NAME,
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

            sa.upload_image_to_project(
                self.PIXEL_PROJECT_NAME,
                f"{self.pixel_folder_path}/{self.EXAMPLE_IMAGE_1}",
                annotation_status="QualityCheck",
            )

            sa.create_annotation_classes_from_classes_json(
                self.PIXEL_PROJECT_NAME, self.pixel_classes_json
            )
            sa.upload_image_annotations(
                project=self.PIXEL_PROJECT_NAME,
                image_name=self.EXAMPLE_IMAGE_1,
                annotation_json=f"{self.pixel_folder_path}/{self.EXAMPLE_IMAGE_1}___pixel.json",
                mask=f"{self.pixel_folder_path}/{self.EXAMPLE_IMAGE_1}___save.png",
            )

            export = sa.prepare_export(self.PIXEL_PROJECT_NAME, include_fuse=True)[
                "name"
            ]
            (temp_dir / "export").mkdir()
            sa.download_export(self.PIXEL_PROJECT_NAME, export, (temp_dir / "export"))

            paths = sa.download_image(
                self.PIXEL_PROJECT_NAME,
                self.EXAMPLE_IMAGE_1,
                temp_dir,
                include_annotations=True,
                include_fuse=True,
            )
            im1 = Image.open(temp_dir / "export" / f"{self.EXAMPLE_IMAGE_1}___fuse.png")
            im1_array = np.array(im1)

            im2 = Image.open(paths[2][0])
            im2_array = np.array(im2)

            self.assertEqual(im1_array.shape, im2_array.shape)
            self.assertEqual(im1_array.dtype, im2_array.dtype)
            self.assertTrue(np.array_equal(im1_array, im2_array))

    @pytest.mark.flaky(reruns=4)
    def test_fuse_image_create_pixel_with_no_classes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = pathlib.Path(temp_dir)

            sa.upload_image_to_project(
                self.PIXEL_PROJECT_NAME_FOR_FUSE,
                f"{self.pixel_folder_path}/{self.EXAMPLE_IMAGE_1}",
                annotation_status="QualityCheck",
            )
            sa.upload_image_annotations(
                project=self.PIXEL_PROJECT_NAME_FOR_FUSE,
                image_name=self.EXAMPLE_IMAGE_1,
                annotation_json=f"{self.pixel_folder_path}/{self.EXAMPLE_IMAGE_1}___pixel.json",
                mask=f"{self.pixel_folder_path}/{self.EXAMPLE_IMAGE_1}___save.png",
            )

            sa.download_image(
                self.PIXEL_PROJECT_NAME_FOR_FUSE,
                self.EXAMPLE_IMAGE_1,
                temp_dir,
                include_annotations=True,
                include_fuse=True,
            )
