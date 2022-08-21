import tempfile
from collections import defaultdict
from pathlib import Path
import os
from os.path import join
import json
import pytest
from unittest.mock import patch
from unittest.mock import MagicMock

from src.superannotate import SAClient
sa = SAClient()
from superannotate_schemas.schemas.base import CreationTypeEnum
from tests.integration.base import BaseTestCase


class TestAnnotationUploadVector(BaseTestCase):
    PROJECT_NAME = "TestAnnotationUploadVectorPreProcessing"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    S3_FOLDER_PATH = "sample_project_pixel"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    IMAGE_NAME = "example_image_1.jpg"

    @property
    def folder_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.TEST_FOLDER_PATH)

    @pytest.mark.flaky(reruns=2)
    def test_annotation_last_action_and_creation_type(self):
        annotation_path = join(self.folder_path, f"{self.IMAGE_NAME}___objects.json")
        sa.upload_image_to_project(self.PROJECT_NAME, join(self.folder_path, self.IMAGE_NAME))
        sa.upload_image_annotations(self.PROJECT_NAME, self.IMAGE_NAME, annotation_path)
        with tempfile.TemporaryDirectory() as tmp_dir:
            sa.download_image_annotations(self.PROJECT_NAME, self.IMAGE_NAME, tmp_dir)
            annotation = json.load(open(join(tmp_dir, f"{self.IMAGE_NAME}___objects.json")))
            for instance in annotation["instances"]:
                self.assertEqual(instance["creationType"], CreationTypeEnum.PRE_ANNOTATION.value)
            assert annotation["metadata"]["lastAction"]["email"] == sa.controller.team_data.creator_id
            self.assertEqual(
                type(annotation["metadata"]["lastAction"]["timestamp"]),
                int
            )

