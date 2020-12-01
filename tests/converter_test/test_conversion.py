from pathlib import Path

import superannotate as sa


# COCO to SA
# test panoptic-segmentation
def test_panoptic_segmentation_coco2sa(tmpdir):
    input_dir = Path(
        "tests"
    ) / "converter_test" / "COCO" / "input" / "toSuperAnnotate" / "panoptic_segmentation"
    out_path = Path(tmpdir) / "toSuperAnnotate" / "panoptic_test"
    sa.import_annotation(
        input_dir, out_path, "COCO", "panoptic_test", "Pixel",
        "panoptic_segmentation"
    )


# test keypoint-detection
def test_keypoint_detection_coco2sa(tmpdir):
    input_dir = Path(
        "tests"
    ) / "converter_test" / "COCO" / "input" / "toSuperAnnotate" / "keypoint_detection"
    out_path = Path(tmpdir) / "toSuperAnnotate" / "keypoint_test"
    sa.import_annotation(
        input_dir, out_path, "COCO", "person_keypoints_test", "Vector",
        "keypoint_detection"
    )


# test instance segmentation
def test_instance_segmentation_coco2sa(tmpdir):
    input_dir = Path(
        "tests"
    ) / "converter_test" / "COCO" / "input" / "toSuperAnnotate" / "instance_segmentation"
    out_path = Path(tmpdir) / "toSuperAnnotate" / "instances_test"
    sa.import_annotation(
        input_dir, out_path, "COCO", "instances_test", "Vector",
        "instance_segmentation"
    )


# SA to COCO
# test panoptic segmentation
def test_panoptic_segmentation_sa2coco(tmpdir):
    input_dir = Path(
        "tests"
    ) / "converter_test" / "COCO" / "input" / "fromSuperAnnotate" / "cats_dogs_panoptic_segm"
    out_path = Path(tmpdir) / "fromSuperAnnotate" / "panoptic_test"
    sa.export_annotation(
        input_dir, out_path, "COCO", "panoptic_test", "Pixel",
        "panoptic_segmentation"
    )


def test_keypoint_detection_sa2coco(tmpdir):
    input_dir = Path(
        "tests"
    ) / "converter_test" / "COCO" / "input" / "fromSuperAnnotate" / "cats_dogs_vector_keypoint_det"
    out_path = Path(tmpdir) / "fromSuperAnnotate" / "keypoint_test_vector"
    sa.export_annotation(
        input_dir, out_path, "COCO", "keypoint_test_vector", "Vector",
        "keypoint_detection"
    )


def test_instance_segmentation_sa2coco_pixel(tmpdir):
    input_dir = Path(
        "tests"
    ) / "converter_test" / "COCO" / "input" / "fromSuperAnnotate" / "cats_dogs_pixel_instance_segm"
    out_path = Path(tmpdir) / "fromSuperAnnotate" / "instance_test_pixel"
    sa.export_annotation(
        input_dir, out_path, "COCO", "instance_test_pixel", "Pixel",
        "instance_segmentation"
    )


def test_instance_segmentation_sa2coco_vector(tmpdir):
    input_dir = Path(
        "tests"
    ) / "converter_test" / "COCO" / "input" / "fromSuperAnnotate" / "cats_dogs_vector_instance_segm"
    out_path = Path(tmpdir) / "fromSuperAnnotate" / "instance_test_vector"
    sa.export_annotation(
        input_dir, out_path, "COCO", "instance_test_vector", "Vector",
        "instance_segmentation"
    )
