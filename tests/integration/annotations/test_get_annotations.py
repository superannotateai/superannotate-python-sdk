import json
import os
from pathlib import Path
from typing import List

import pytest
from pydantic import parse_obj_as
from superannotate_schemas.schemas.internal import VectorAnnotation

import src.superannotate as sa
from tests.integration.base import BaseTestCase


class TestGetAnnotations(BaseTestCase):
    PROJECT_NAME = "Test-get_annotations"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    IMAGE_NAME = "example_image_1.jpg"

    @property
    def folder_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.TEST_FOLDER_PATH)

    @pytest.mark.flaky(reruns=3)
    def test_get_annotations(self):
        sa.init()
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        _, _, _ = sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path
        )

        annotations = sa.get_annotations(f"{self.PROJECT_NAME}", [self.IMAGE_NAME])
        self.assertEqual(len(annotations), 1)
        with open(f"{self.folder_path}/{self.IMAGE_NAME}___objects.json", "r") as annotation_file:
            annotation_data = json.load(annotation_file)
            self.assertEqual(len(annotation_data["instances"]), len(annotations[0]["instances"]))
        parse_obj_as(List[VectorAnnotation], annotations)

    @pytest.mark.flaky(reruns=3)
    def test_get_annotations_all(self):
        sa.init()
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        _, _, _ = sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path
        )
        annotations = sa.get_annotations(f"{self.PROJECT_NAME}")
        self.assertEqual(len(annotations), 4)
