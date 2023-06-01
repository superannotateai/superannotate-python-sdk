import filecmp
import tempfile
from unittest import TestCase

from src.superannotate import export_annotation
from tests.integration.convertors import DATA_SET_PATH


class TestExportInstanceSegmentation(TestCase):
    DATA_SET_NAME = "TestVectorAnnotationImage"
    VECTOR_DATA_PATH = DATA_SET_PATH / "sample_project_vector"
    VECTOR_DATA_OBJECTS_JSON_PATH = DATA_SET_PATH / "sample_project_vector_objects_json"
    COCO_INSTANCE_SEGMENTATION = DATA_SET_PATH / "coco_instance_segmentation"

    def test_convertor(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            export_annotation(
                self.VECTOR_DATA_PATH,
                tmp_dir,
                dataset_name=self.DATA_SET_NAME,
                dataset_format="COCO",
                project_type="Vector",
                task="instance_segmentation",
            )
            dircmp = filecmp.dircmp(
                DATA_SET_PATH / self.COCO_INSTANCE_SEGMENTATION,
                tmp_dir,
            )
            assert not any([dircmp.left_only, dircmp.right_only])

    def test_convertor_objects_json(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            export_annotation(
                self.VECTOR_DATA_OBJECTS_JSON_PATH,
                tmp_dir,
                dataset_name=self.DATA_SET_NAME,
                dataset_format="COCO",
                project_type="Vector",
                task="instance_segmentation",
            )
            dircmp = filecmp.dircmp(
                DATA_SET_PATH / self.COCO_INSTANCE_SEGMENTATION,
                tmp_dir,
            )
            assert not any([dircmp.left_only, dircmp.right_only])
