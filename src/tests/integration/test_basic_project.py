import json
import os
import tempfile
from os.path import dirname
from pathlib import Path

import src.lib.app.superannotate as sa
from src.tests.integration.base import BaseTestCase


class TestProject(BaseTestCase):
    PROJECT_NAME = "sample_project"
    PROJECT_TYPE = "Pixel"
    PROJECT_DESCRIPTION = "DESCRIPTION"
    TEST_IMAGE_NAME = "example_image_1.jpg"
    TEST_FOLDER_PTH = "data_set/sample_project_pixel"
    TEST_ANNOTATION_PATH = "data_set/sample_annotation_no_class"

    @property
    def folder_path(self):
        return Path(
            Path(os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PTH))
        )

    @property
    def annotations_path(self):
        return Path(
            Path(os.path.join(dirname(dirname(__file__)), self.TEST_ANNOTATION_PATH))
        )

    @property
    def classes_json_path(self):
        return self.folder_path / "classes" / "classes.json"

    def test_basic_project(self):

        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )

        count_in_folder = len(list(self.folder_path.glob("*.jpg"))) + len(
            list(self.folder_path.glob("*.png"))
        )
        count_in_folder -= len(list(self.folder_path.glob("*___fuse.png")))
        if self.PROJECT_TYPE == "Pixel":
            count_in_folder -= len(list(self.folder_path.glob("*___save.png")))
        images = sa.search_images(self.PROJECT_NAME)
        assert count_in_folder == len(images)

        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.classes_json_path
        )
        classes_in_file = json.load(open(self.classes_json_path))
        classes_in_project = sa.search_annotation_classes(self.PROJECT_NAME)
        with tempfile.TemporaryDirectory() as temp_dir:
            json.dump(classes_in_project, open(Path(temp_dir) / "tmp_c.json", "w"))
            self.assertEqual(len(classes_in_file), len(classes_in_project))
            for cl_f in classes_in_file:
                found = False
                for cl_c in classes_in_project:
                    if cl_f["name"] == cl_c["name"]:
                        found = True
                        break
                assert found

            sa.upload_annotations_from_folder_to_project(
                self.PROJECT_NAME, self.folder_path
            )

            export = sa.prepare_export(self.PROJECT_NAME)

            sa.download_export(self.PROJECT_NAME, export, temp_dir)
            for image in self.folder_path.glob("*.[jpg|png]"):
                found = False
                for image_in_project in Path(temp_dir).glob("*.jpg"):
                    if image.name == image_in_project.name:
                        found = True
                        break
                assert found, image

            for json_in_folder in self.folder_path.glob("*.json"):
                found = False
                for json_in_project in Path(temp_dir).glob("*.json"):
                    if json_in_folder.name == json_in_project.name:
                        found = True
                        break
                assert found, json_in_folder
            if self.PROJECT_TYPE == "Pixel":
                for mask_in_folder in self.folder_path.glob("*___save.png"):
                    found = False
                    for mask_in_project in Path(temp_dir).glob("*___save.png"):
                        if mask_in_folder.name == mask_in_project.name:
                            found = True
                            break
                    self.assertTrue(found and mask_in_folder)

    def test_upload_annotations(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.annotations_path, annotation_status="InProgress"
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.classes_json_path
        )
        sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path
        )
        annotations = sa.get_image_annotations(
            str(self.folder_path), self.TEST_IMAGE_NAME
        )
        truth_path = self.annotations_path / "truth.json"
        with open(truth_path) as f:
            data = json.loads(f.read())
        self.assertEqual(data, annotations)
