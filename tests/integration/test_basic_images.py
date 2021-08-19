import json
import os
import tempfile
from os.path import dirname
from pathlib import Path

import src.superannotate as sa
from tests.integration.base import BaseTestCase


class TestPixelImages(BaseTestCase):
    PROJECT_NAME = "sample_project_pixel"
    PROJECT_TYPE = "Pixel"
    PROJECT_DESCRIPTION = "Example Project test pixel basic images"
    TEST_FOLDER_PTH = "data_set/sample_project_pixel"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PTH)

    @property
    def classes_json_path(self):
        return f"{self.folder_path}/classes/classes.json"

    def test_basic_images(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            sa.upload_images_from_folder_to_project(
                self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
            )
            sa.create_annotation_classes_from_classes_json(
                self.PROJECT_NAME, self.classes_json_path
            )
            images = sa.search_images(self.PROJECT_NAME, "example_image_1")
            self.assertEqual(len(images), 1)

            image_name = images[0]
            downloaded = sa.download_image(
                self.PROJECT_NAME, image_name, temp_dir, True
            )
            self.assertEqual(downloaded[1], (None, None))
            self.assertGreater(len(downloaded[0]), 0)

            sa.download_image_annotations(self.PROJECT_NAME, image_name, temp_dir)
            self.assertEqual(len(list(Path(temp_dir).glob("*"))), 0)

            sa.upload_image_annotations(
                project=self.PROJECT_NAME,
                image_name=image_name,
                annotation_json=sa.image_path_to_annotation_paths(
                    f"{self.folder_path}/{image_name}", self.PROJECT_TYPE
                )[0],
                mask=None
                if self.PROJECT_TYPE == "Vector"
                else sa.image_path_to_annotation_paths(
                    f"{self.folder_path}/{image_name}", self.folder_path
                )[1],
            )

            self.assertIsNotNone(
                sa.get_image_annotations(self.PROJECT_NAME, image_name)[
                    "annotation_json_filename"
                ]
            )

            sa.download_image_annotations(self.PROJECT_NAME, image_name, temp_dir)
            annotation = list(Path(temp_dir).glob("*.json"))
            self.assertEqual(len(annotation), 1)
            annotation = json.load(open(annotation[0]))

            sa.download_annotation_classes_json(self.PROJECT_NAME, temp_dir)
            downloaded_classes = json.load(open(f"{temp_dir}/classes.json"))

            for a in annotation["instances"]:
                if "className" not in a:
                    continue
                for c1 in downloaded_classes:
                    if (
                        a["className"] == c1["name"]
                        or a["className"] == "Personal vehicle1"
                    ):  # "Personal vehicle1" is not existing class in annotations
                        break
                else:
                    assert False

            input_classes = json.load(open(self.classes_json_path))
            assert len(downloaded_classes) == len(input_classes)
            for c1 in downloaded_classes:
                found = False
                for c2 in input_classes:
                    if c1["name"] == c2["name"]:
                        found = True
                        break
                assert found


class TestVectorImages(BaseTestCase):
    PROJECT_NAME = "sample_project_vector"
    PROJECT_TYPE = "Vector"
    PROJECT_DESCRIPTION = "Example Project test vector basic images"
    TEST_FOLDER_PTH = "data_set/sample_project_vector"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PTH)

    @folder_path.setter
    def folder_path(self, value):
        self._folder_path = value

    @property
    def classes_json_path(self):
        return f"{self.folder_path}/classes/classes.json"

    def test_basic_images(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            sa.upload_images_from_folder_to_project(
                self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
            )
            sa.create_annotation_classes_from_classes_json(
                self.PROJECT_NAME, self.classes_json_path
            )
            images = sa.search_images(self.PROJECT_NAME, "example_image_1")
            self.assertEqual(len(images), 1)

            image_name = images[0]
            sa.download_image(self.PROJECT_NAME, image_name, temp_dir, True)
            self.assertEqual(
                sa.get_image_annotations(self.PROJECT_NAME, image_name)[
                    "annotation_json"
                ],
                None,
            )
            sa.download_image_annotations(self.PROJECT_NAME, image_name, temp_dir)
            sa.upload_image_annotations(
                project=self.PROJECT_NAME,
                image_name=image_name,
                annotation_json=sa.image_path_to_annotation_paths(
                    f"{self.folder_path}/{image_name}", self.PROJECT_TYPE
                )[0],
                mask=None
                if self.PROJECT_TYPE == "Vector"
                else sa.image_path_to_annotation_paths(
                    f"{self.folder_path}/{image_name}", self.folder_path
                )[1],
            )

            self.assertIsNotNone(
                sa.get_image_annotations(self.PROJECT_NAME, image_name)[
                    "annotation_json_filename"
                ]
            )

            sa.download_image_annotations(self.PROJECT_NAME, image_name, temp_dir)
            annotation = list(Path(temp_dir).glob("*.json"))
            self.assertEqual(len(annotation), 1)
            annotation = json.load(open(annotation[0]))

            sa.download_annotation_classes_json(self.PROJECT_NAME, temp_dir)
            downloaded_classes = json.load(open(f"{temp_dir}/classes.json"))

            for a in annotation:
                if "className" not in a:
                    continue
                for c1 in downloaded_classes:
                    if (
                        a["className"] == c1["name"]
                        or a["className"] == "Personal vehicle1"
                    ):  # "Personal vehicle1" is not existing class in annotations
                        break
                else:
                    assert False

            input_classes = json.load(open(self.classes_json_path))
            assert len(downloaded_classes) == len(input_classes)
            for c1 in downloaded_classes:
                found = False
                for c2 in input_classes:
                    if c1["name"] == c2["name"]:
                        found = True
                        break
                assert found
