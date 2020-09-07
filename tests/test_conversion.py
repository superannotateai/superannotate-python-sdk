import superannotate as sa


# COCO to SA
# test panoptic-segmentation
def panoptic_segmentation_coco2sa():
    try:
        sa.convert_annotation_format_from(
            "converter_test/COCO/input/toSuperAnnotate/panoptic_segmentation",
            "converter_test/COCO/output/toSuperAnnotate/panoptic_test", "COCO",
            "panoptic_test", "pixel", "panoptic_segmentation"
        )
    except Exception as e:
        return 1
    return 0


# test keypoint-detection
def keypoint_detection_coco2sa():
    try:
        sa.convert_annotation_format_from(
            "converter_test/COCO/input/toSuperAnnotate/keypoint_detection",
            "converter_test/COCO/output/toSuperAnnotate/keypoint_test", "COCO",
            "person_keypoints_test", "vector", "keypoint_detection"
        )
    except Exception as e:
        return 1
    return 0


# test instance segmentation
def instance_segmentation_coco2sa():
    try:
        sa.convert_annotation_format_from(
            "converter_test/COCO/input/toSuperAnnotate/instance_segmentation",
            "converter_test/COCO/output/toSuperAnnotate/instances_test",
            "COCO", "instances_test", "vector", "instance_segmentation"
        )
    except Exception as e:
        return 1
    return 0


# SA to COCO
# test panoptic segmentation
def panoptic_segmentation_sa2coco():
    try:
        sa.convert_annotation_format_to(
            "converter_test/COCO/input/fromSuperAnnotate/cats_dogs_panoptic_segm",
            "converter_test/COCO/output/fromSuperAnnotate/panoptic_test",
            "COCO", "panoptic_test", "pixel", "panoptic_segmentation"
        )
    except Exception as e:
        return 1
    return 0


def keypoint_detection_sa2coco():
    try:
        sa.convert_annotation_format_to(
            "converter_test/COCO/input/fromSuperAnnotate/cats_dogs_vector_keypoint_det",
            "converter_test/COCO/output/fromSuperAnnotate/keypoint_test_vector",
            "COCO", "keypoint_test_vector", "vector", "keypoint_detection"
        )
    except Exception as e:
        return 1
    return 0


def instance_segmentation_sa2coco_pixel():
    try:
        sa.convert_annotation_format_to(
            "converter_test/COCO/input/fromSuperAnnotate/cats_dogs_pixel_instance_segm",
            "converter_test/COCO/output/fromSuperAnnotate/instance_test_pixel",
            "COCO", "instance_test_pixel", "pixel", "instance_segmentation"
        )
    except Exception as e:
        return 1
    return 0


def instance_segmentation_sa2coco_vector():
    try:
        sa.convert_annotation_format_to(
            "converter_test/COCO/input/fromSuperAnnotate/cats_dogs_vector_instance_segm",
            "converter_test/COCO/output/fromSuperAnnotate/instance_test_vector",
            "COCO", "instance_test_vector", "vector", "instance_segmentation"
        )
    except Exception as e:
        return 1
    return 0


def test_coco2sa():
    assert panoptic_segmentation_coco2sa() == 0
    assert keypoint_detection_coco2sa() == 0
    assert instance_segmentation_coco2sa() == 0


def test_sa2coco():
    assert panoptic_segmentation_sa2coco() == 0
    assert keypoint_detection_sa2coco() == 0
    assert instance_segmentation_sa2coco_pixel() == 0
    assert instance_segmentation_sa2coco_vector() == 0


def test_pipline():
    pass




