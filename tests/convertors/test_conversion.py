import json
import os
import tempfile
from os.path import dirname
from pathlib import Path
from unittest import TestCase
import pytest

from src.superannotate import SAClient
sa = SAClient()


class TestCocoSplit(TestCase):
    TEST_FOLDER_PATH = "data_set/converter_test/COCO/input/toSuperAnnotate"
    TEST_BASE_FOLDER_PATH = "data_set/converter_test"

    @property
    def base_folder_path(self):
        return Path(
            Path(os.path.join(dirname(dirname(__file__)), self.TEST_BASE_FOLDER_PATH))
        )

    @property
    def folder_path(self):
        return Path(
            Path(os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH))
        )

    def test_panoptic_segmentation_coco2sa(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_dir = self.folder_path / "panoptic_segmentation"
            out_path = Path(tmp_dir) / "toSuperAnnotate" / "panoptic_test"
            sa.import_annotation(
                input_dir,
                out_path,
                "COCO",
                "panoptic_test",
                "Pixel",
                "panoptic_segmentation",
            )

    def test_keypoint_detection_coco2sa(self):
        """
        test keypoint-detection
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_dir = self.folder_path / "keypoint_detection"
            out_path = Path(tmp_dir) / "toSuperAnnotate" / "keypoint_test"
            sa.import_annotation(
                input_dir,
                out_path,
                "COCO",
                "person_keypoints_test",
                "Vector",
                "keypoint_detection",
            )

    def test_keypoint_detection_coco2sa_multi_template(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_dir = self.folder_path / "keypoint_detection_multi_template"
            out_path = (
                Path(tmp_dir) / "toSuperAnnotate" / "keypoint_detection_multi_template"
            )

            sa.import_annotation(
                input_dir,
                out_path,
                "COCO",
                "keypoint_multi_template_test",
                "Vector",
                "keypoint_detection",
            )
            import json

            with open(str(Path(input_dir) / "truth.json")) as f:
                truth = json.loads(f.read())

            with open(
                str(
                    Path(out_path)
                    / "68307_47130_68308_47130_68307_47131_68308_47131_0.png___objects.json"
                )
            ) as f:
                data = json.loads(f.read())
            self.assertEqual(data, truth)

    def test_instance_segmentation_coco2sa(self):
        """
        test instance segmentation
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_dir = self.folder_path / "instance_segmentation"
            out_path = Path(tmp_dir) / "toSuperAnnotate" / "instances_test"
            sa.import_annotation(
                input_dir,
                out_path,
                "COCO",
                "instances_test",
                "Vector",
                "instance_segmentation",
            )

    def test_pan_optic_segmentation_sa2coco(self):
        """
        # SA to COCO
        # test panoptic segmentation
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_dir = (
                self.base_folder_path
                / "COCO"
                / "input"
                / "fromSuperAnnotate"
                / "cats_dogs_panoptic_segm"
            )
            out_path = Path(tmp_dir) / "fromSuperAnnotate" / "panoptic_test"
            sa.export_annotation(
                input_dir,
                out_path,
                "COCO",
                "panoptic_test",
                "Pixel",
                "panoptic_segmentation",
            )

    def test_keypoint_detection_sa2coco(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_dir = (
                self.base_folder_path
                / "COCO"
                / "input"
                / "fromSuperAnnotate"
                / "cats_dogs_vector_keypoint_det"
            )
            out_path = Path(tmp_dir) / "fromSuperAnnotate" / "keypoint_test_vector"
            sa.export_annotation(
                input_dir,
                out_path,
                "COCO",
                "keypoint_test_vector",
                "Vector",
                "keypoint_detection",
            )

    def test_instance_segmentation_sa2coco_pixel(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_dir = (
                self.base_folder_path
                / "COCO"
                / "input"
                / "fromSuperAnnotate"
                / "cats_dogs_pixel_instance_segm"
            )
            out_path = Path(tmp_dir) / "fromSuperAnnotate" / "instance_test_pixel"
            sa.export_annotation(
                input_dir,
                out_path,
                "COCO",
                "instance_test_pixel",
                "Pixel",
                "instance_segmentation",
            )

    def test_instance_segmentation_sa2coco_vector(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_dir = (
                self.base_folder_path
                / "COCO"
                / "input"
                / "fromSuperAnnotate"
                / "cats_dogs_vector_instance_segm"
            )
            out_path = Path(tmp_dir) / "fromSuperAnnotate" / "instance_test_vector"
            sa.export_annotation(
                input_dir,
                out_path,
                "COCO",
                "instance_test_vector",
                "Vector",
                "instance_segmentation",
            )

    def test_instance_segmentation_sa2coco_vector_empty_array(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_dir = (
                self.base_folder_path
                / "COCO"
                / "input"
                / "fromSuperAnnotate"
                / "cats_dogs_vector_instance_segm_empty_array"
            )
            out_path = (
                Path(tmp_dir)
                / "empty_array"
                / "fromSuperAnnotate"
                / "instance_test_vector"
            )
            sa.export_annotation(
                input_dir,
                out_path,
                "COCO",
                "instance_test_vector",
                "Vector",
                "instance_segmentation",
            )
            json_path = out_path / "instance_test_vector.json"
            with open(json_path) as f:
                data = json.loads(f.read())
            truth_path = input_dir / "truth.json"
            with open(truth_path) as f:
                truth = json.loads(f.read())
            data["info"]["date_created"] = 0
            truth["info"]["date_created"] = 0
            self.assertEqual(truth, data)

    def test_instance_segmentation_sa2coco_vector_empty_name(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_dir = (
                self.base_folder_path
                / "COCO"
                / "input"
                / "fromSuperAnnotate"
                / "vector_no_name"
            )
            out_path = (
                Path(tmp_dir)
                / "empty_name"
                / "fromSuperAnnotate"
                / "instance_test_vector"
            )
            sa.export_annotation(
                input_dir,
                out_path,
                "COCO",
                "instance_test_vector",
                "Vector",
                "instance_segmentation",
            )

    @pytest.mark.skip(reason="Need to adjust")
    def test_upload_annotations_with_template_id(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmpdir = Path(tmp_dir)
            project_name = "test_templates"
            for project in sa.search_projects(project_name):
                sa.delete_project(project)
            project = sa.create_project(project_name, "test", "Vector")
            input_dir = self.base_folder_path / "sample_coco_with_templates"
            sa.upload_images_from_folder_to_project(project, input_dir)
            out_path = (
                Path(tmpdir) / "toSuperAnnotate" / "keypoint_detection_multi_template"
            )

            sa.import_annotation(
                input_dir,
                out_path,
                "COCO",
                "sample_coco",
                "Vector",
                "keypoint_detection",
            )
            sa.upload_annotations_from_folder_to_project(project, out_path)
            annotations = sa.get_annotations(project_name, "t.png")[0]
            assert annotations[0]["instances"][0]["templateId"] == -1
