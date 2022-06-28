import json
import os
import tempfile
from pathlib import Path

import pytest

from src.superannotate import SAClient
sa = SAClient()
from tests import DATA_SET_PATH
from tests.integration.base import BaseTestCase


class TestWorkflowGet(BaseTestCase):
    PROJECT_NAME = "TestWorkflowGet"
    PROJECT_TYPE = "Vector"
    PROJECT_DESCRIPTION = "DESCRIPTION"

    def test_workflow_get(self):
        sa.create_annotation_class(
            self.PROJECT_NAME,
            "class1",
            "#FFAAFF",
            [
                {
                    "name": "tall",
                    "is_multiselect": 0,
                    "attributes": [{"name": "yes"}, {"name": "no"}],
                },
                {
                    "name": "age",
                    "is_multiselect": 0,
                    "attributes": [{"name": "young"}, {"name": "old"}],
                },
            ],
        )
        sa.create_annotation_class(
            self.PROJECT_NAME,
            "class2",
            "#FFAAFF",
            [
                {
                    "name": "tall",
                    "is_multiselect": 0,
                    "attributes": [{"name": "yes"}, {"name": "no"}],
                },
                {
                    "name": "age",
                    "is_multiselect": 0,
                    "attributes": [{"name": "young"}, {"name": "old"}],
                },
            ],
        )
        sa.set_project_workflow(
            self.PROJECT_NAME,
            [
                {
                    "step": 1,
                    "className": "class1",
                    "tool": 3,
                    "attribute": [
                        {
                            "attribute": {
                                "name": "young",
                                "attribute_group": {"name": "age"},
                            }
                        },
                        {
                            "attribute": {
                                "name": "yes",
                                "attribute_group": {"name": "tall"},
                            }
                        },
                    ],
                },
                {
                    "step": 2,
                    "className": "class2",
                    "tool": 3,
                    "attribute": [
                        {
                            "attribute": {
                                "name": "young",
                                "attribute_group": {"name": "age"},
                            }
                        },
                        {
                            "attribute": {
                                "name": "yes",
                                "attribute_group": {"name": "tall"},
                            }
                        },
                    ],
                }
            ],
        )
        workflows = sa.get_project_workflow(self.PROJECT_NAME)
        self.assertEqual(workflows[0]['className'], "class1")
        self.assertEqual(workflows[1]['className'], "class2")


class TestProject(BaseTestCase):
    PROJECT_NAME = "sample_basic_project"
    PROJECT_TYPE = "Pixel"
    PROJECT_DESCRIPTION = "DESCRIPTION"
    TEST_IMAGE_NAME = "example_image_1.jpg"
    TEST_FOLDER_PATH = "sample_project_pixel"
    TEST_ANNOTATION_PATH = "sample_annotation_no_class"
    PNG_POSTFIX = "*___save.png"
    FUSE_PNG_POSTFIX = "*___fuse.png"

    @property
    def folder_path(self):
        return Path(
            Path(os.path.join(DATA_SET_PATH, self.TEST_FOLDER_PATH))
        )

    @property
    def annotations_path(self):
        return Path(
            Path(os.path.join(DATA_SET_PATH, self.TEST_ANNOTATION_PATH))
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
        count_in_folder -= len(list(self.folder_path.glob(self.FUSE_PNG_POSTFIX)))
        count_in_folder -= len(list(self.folder_path.glob(self.PNG_POSTFIX)))
        images = sa.search_items(self.PROJECT_NAME)
        assert count_in_folder == len(images)

        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.classes_json_path
        )
        classes_in_file = json.load(open(self.classes_json_path))
        classes_in_project = sa.search_annotation_classes(self.PROJECT_NAME)
        with tempfile.TemporaryDirectory() as temp_dir:
            json.dump(classes_in_project, open(Path(temp_dir) / "tmp_c.json", "w"))
            self.assertEqual(len(classes_in_file), len(classes_in_project))
            classes_in_file_names = [
                annotation_class["name"] for annotation_class in classes_in_file
            ]
            classes_in_project_names = [
                annotation_class["name"] for annotation_class in classes_in_project
            ]
            self.assertTrue(set(classes_in_file_names) & set(classes_in_project_names))

            sa.upload_annotations_from_folder_to_project(
                self.PROJECT_NAME, str(self.folder_path)
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
                for mask_in_folder in self.folder_path.glob(self.PNG_POSTFIX):
                    found = False
                    for mask_in_project in Path(temp_dir).glob(self.PNG_POSTFIX):
                        if mask_in_folder.name == mask_in_project.name:
                            found = True
                            break
                    self.assertTrue(found and mask_in_folder)

    @pytest.mark.skip(reason="response from backend does not match with expected")
    def test_upload_annotations(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.annotations_path, annotation_status="InProgress"
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.classes_json_path
        )
        sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, str(self.folder_path)
        )
        annotations = sa.get_annotations(self.PROJECT_NAME, [self.TEST_IMAGE_NAME])[0]
        truth_path = self.annotations_path / "truth.json"
        with open(truth_path) as f:
            data = json.loads(f.read())
        self.assertEqual(data, annotations)
