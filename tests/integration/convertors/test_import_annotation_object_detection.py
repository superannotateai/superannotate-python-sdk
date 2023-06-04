import filecmp
import json
import os
import tempfile
from unittest import TestCase

from jsoncomparison import Compare
from jsoncomparison import NO_DIFF
from src.superannotate import import_annotation
from tests.integration.convertors import DATA_SET_PATH


class TestImportObjectDetection(TestCase):
    DATA_SET_NAME = "TestVectorAnnotationImage"
    VECTOR_DATA_PATH = DATA_SET_PATH / "coco_to_sa_object_detection_expected_result"
    COCO_OBJECT_DETECTION = DATA_SET_PATH / "coco_object_detection"

    def test_convertor(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            import_annotation(
                self.COCO_OBJECT_DETECTION,
                tmp_dir,
                dataset_name=self.DATA_SET_NAME,
                dataset_format="COCO",
                project_type="Vector",
                task="object_detection",
            )
            dircmp = filecmp.dircmp(
                self.VECTOR_DATA_PATH,
                tmp_dir,
            )
            assert not any([dircmp.left_only, dircmp.right_only])

            json_files = [
                pos_json
                for pos_json in os.listdir(self.VECTOR_DATA_PATH)
                if pos_json.endswith(".json")
            ]
            tmp_json_files = [
                pos_json
                for pos_json in os.listdir(tmp_dir)
                if pos_json.endswith(".json")
            ]
            assert len(json_files) == len(tmp_json_files)

            for i in range(len(json_files)):
                with open(
                    f"{self.VECTOR_DATA_PATH}/{json_files[i]}"
                ) as json_file, open(f"{tmp_dir}/{tmp_json_files[i]}") as tmp_json_file:
                    expected_data = json.load(json_file)
                    actual_data = json.load(tmp_json_file)

                    rules = {"instances": {"_list": ["classId"]}}
                    diff = Compare(rules=rules).check(expected_data, actual_data)
                    assert diff == NO_DIFF
