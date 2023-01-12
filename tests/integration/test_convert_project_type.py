import os
import json
import tempfile
from pathlib import Path
from tests import DATA_SET_PATH

from src.superannotate import convert_project_type
from unittest import TestCase


class TestConvertProjectType(TestCase):
    TEST_FOLDER_PATH = 'pixel_with_holes'
    FIRST_IMAGE = '1.jpg'
    SECOND_IMAGE = '2.webp'

    @property
    def folder_path(self):
        return os.path.join(DATA_SET_PATH, self.TEST_FOLDER_PATH)

    def test_convert_pixel_with_holes_to_vector(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            convert_project_type(self.folder_path, temp_dir)
            assert len(list(Path(temp_dir).glob("*"))) == 5
            annotation_files = [i.name for i in Path(temp_dir).glob("*___objects.json")]
            assert len(annotation_files) == 2
            with open(os.path.join(temp_dir, f"{self.SECOND_IMAGE}___objects.json")) as file:
                data = json.load(file)
                assert len(data['instances'][0]['exclude']) == 4



