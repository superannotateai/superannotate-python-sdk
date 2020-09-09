import shutil

import superannotate as sa


# COCO to SA
# test panoptic-segmentation
def panoptic_segmentation_coco2sa(tmpdir):
    out_path = tmpdir / "toSuperAnnotate/panoptic_test"
    try:
        sa.import_annotation_format(
            "tests/converter_test/COCO/input/toSuperAnnotate/panoptic_segmentation",
            str(out_path), "COCO", "panoptic_test", "Pixel",
            "panoptic_segmentation"
        )
    except Exception as e:
        return 1
    return 0


# test keypoint-detection
def keypoint_detection_coco2sa(tmpdir):
    out_path = tmpdir / "toSuperAnnotate/keypoint_test"
    try:
        sa.import_annotation_format(
            "tests/converter_test/COCO/input/toSuperAnnotate/keypoint_detection",
            str(out_path), "COCO", "person_keypoints_test", "Vector",
            "keypoint_detection"
        )
    except Exception as e:
        return 1
    return 0


# test instance segmentation
def instance_segmentation_coco2sa(tmpdir):
    out_path = tmpdir / "toSuperAnnotate/instances_test"
    try:
        sa.import_annotation_format(
            "tests/converter_test/COCO/input/toSuperAnnotate/instance_segmentation",
            str(out_path), "COCO", "instances_test", "Vector",
            "instance_segmentation"
        )
    except Exception as e:
        return 1
    return 0


# SA to COCO
# test panoptic segmentation
def panoptic_segmentation_sa2coco(tmpdir):
    out_path = tmpdir / "fromSuperAnnotate/panoptic_test"
    try:
        sa.export_annotation_format(
            "tests/converter_test/COCO/input/fromSuperAnnotate/cats_dogs_panoptic_segm",
            str(out_path), "COCO", "panoptic_test", "Pixel",
            "panoptic_segmentation"
        )
    except Exception as e:
        return 1
    return 0


def keypoint_detection_sa2coco(tmpdir):
    out_path = tmpdir / "fromSuperAnnotate/keypoint_test_vector"
    try:
        sa.export_annotation_format(
            "tests/converter_test/COCO/input/fromSuperAnnotate/cats_dogs_vector_keypoint_det",
            str(out_path), "COCO", "keypoint_test_vector", "Vector",
            "keypoint_detection"
        )
    except Exception as e:
        return 1
    return 0


def instance_segmentation_sa2coco_pixel(tmpdir):
    out_path = tmpdir / "fromSuperAnnotate/instance_test_pixel"
    try:
        sa.export_annotation_format(
            "tests/converter_test/COCO/input/fromSuperAnnotate/cats_dogs_pixel_instance_segm",
            str(out_path), "COCO", "instance_test_pixel", "Pixel",
            "instance_segmentation"
        )
    except Exception as e:
        return 1
    return 0


def instance_segmentation_sa2coco_vector(tmpdir):
    out_path = tmpdir / "fromSuperAnnotate/instance_test_vector"
    try:
        sa.export_annotation_format(
            "tests/converter_test/COCO/input/fromSuperAnnotate/cats_dogs_vector_instance_segm",
            str(out_path), "COCO", "instance_test_vector", "Vector",
            "instance_segmentation"
        )
    except Exception as e:
        return 1
    return 0


def test_coco2sa(tmpdir):
    assert panoptic_segmentation_coco2sa(tmpdir) == 0
    assert keypoint_detection_coco2sa(tmpdir) == 0
    assert instance_segmentation_coco2sa(tmpdir) == 0


def test_sa2coco(tmpdir):
    assert panoptic_segmentation_sa2coco(tmpdir) == 0
    assert keypoint_detection_sa2coco(tmpdir) == 0
    assert instance_segmentation_sa2coco_pixel(tmpdir) == 0
    assert instance_segmentation_sa2coco_vector(tmpdir) == 0
