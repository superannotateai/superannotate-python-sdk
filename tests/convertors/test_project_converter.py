import json
import os
import tempfile
from os.path import dirname
from pathlib import Path
from unittest import TestCase

from src.superannotate import SAClient
sa = SAClient()


class TestCocoSplit(TestCase):
    TEST_FOLDER_PATH = "data_set"

    @property
    def folder_path(self):
        return Path(
            Path(os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH))
        )

    @staticmethod
    def compare_jsons(json_gen, input_dir):
        for path in json_gen:
            final_json = json.load(open(str(path)))
            input_path = input_dir.joinpath(path.name)
            init_json = json.load(open(str(input_path)))

            for init, final in zip(init_json["instances"], final_json["instances"]):
                for key in init.keys():
                    if key == "parts":
                        continue
                    init_value = init[key]
                    final_value = final[key]
                    assert init_value == final_value

    def test_pixel_vector_pixel(self):
        input_dir = Path()
        input_dir = input_dir.joinpath(
            self.folder_path,
            "converter_test",
            "COCO",
            "input",
            "fromSuperAnnotate",
            "cats_dogs_pixel_instance_segm",
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_dir = Path(tmp_dir) / "output"
            final_dir = Path(tmp_dir) / "output2"

            sa.convert_project_type(input_dir, temp_dir)
            sa.convert_project_type(temp_dir, final_dir)

            gen = final_dir.glob("*.json")
            self.compare_jsons(gen, input_dir)

    def test_vector_pixel_vector(self):
        input_dir = (
            self.folder_path
            / "converter_test"
            / "COCO"
            / "input"
            / "fromSuperAnnotate"
            / "cats_dogs_vector_instance_segm"
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_dir = Path(tmp_dir) / "output"
            final_dir = Path(tmp_dir) / "output2"

            sa.convert_project_type(input_dir, temp_dir)
            sa.convert_project_type(temp_dir, final_dir)

            gen = input_dir.glob("*.json")
            self.compare_jsons(gen, input_dir)
