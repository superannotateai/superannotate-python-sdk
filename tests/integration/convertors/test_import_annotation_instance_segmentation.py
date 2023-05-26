import filecmp
import tempfile
from unittest import TestCase

from src.superannotate import import_annotation
from tests.integration.convertors import DATA_SET_PATH


class TestExportInstanceSegmentation(TestCase):
    DATA_SET_NAME = "TestVectorAnnotationImage"
    VECTOR_DATA_PATH = DATA_SET_PATH / "sample_project_vector"
    COCO_INSTANCE_SEGMENTATION = DATA_SET_PATH / "coco_instance_segmentation"

    def test_convertor(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            import_annotation(
                self.COCO_INSTANCE_SEGMENTATION,
                tmp_dir,
                dataset_name=self.DATA_SET_NAME,
                dataset_format="COCO",
                project_type="Vector",
                task="instance_segmentation",
            )
            dircmp = filecmp.dircmp(
                self.VECTOR_DATA_PATH,
                tmp_dir,
            )
            assert not any([dircmp.left_only, dircmp.right_only])
