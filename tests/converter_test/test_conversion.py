from pathlib import Path
from mixpanel import json_dumps

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


def test_keypoint_detection_coco2sa_multi_template(tmpdir):
    input_dir = Path(
        "tests"
    ) / "converter_test" / "COCO" / "input" / "toSuperAnnotate" / "keypoint_detection_multi_template"
    out_path = Path(
        tmpdir
    ) / "toSuperAnnotate" / "keypoint_detection_multi_template"

    sa.import_annotation(
        input_dir, out_path, "COCO", "keypoint_multi_template_test", "Vector",
        "keypoint_detection"
    )
    import json
    with open(str(Path(input_dir) / "truth.json")) as f:
        truth = json.loads(f.read())

    with open(
        str(
            Path(out_path) /
            "68307_47130_68308_47130_68307_47131_68308_47131_0.png___objects.json"
        )
    ) as f:
        data = json.loads(f.read())
    assert data == truth


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


def test_instance_segmentation_sa2coco_vector_empty_array(tmpdir):
    input_dir = Path(
        "tests"
    ) / "converter_test" / "COCO" / "input" / "fromSuperAnnotate" / "cats_dogs_vector_instance_segm_empty_array"
    out_path = Path(
        tmpdir
    ) / "empty_array" / "fromSuperAnnotate" / "instance_test_vector"
    sa.export_annotation(
        input_dir, out_path, "COCO", "instance_test_vector", "Vector",
        "instance_segmentation"
    )
    import json
    json_path = out_path / "instance_test_vector.json"
    with open(json_path, 'r') as f:
        data = json.loads(f.read())
    truth_path = input_dir / "truth.json"
    with open(truth_path, 'r') as f:
        truth = json.loads(f.read())
    data['info']['date_created'] = 0
    truth['info']['date_created'] = 0
    assert truth == data


def test_instance_segmentation_sa2coco_vector_empty_name(tmpdir):
    input_dir = Path(
        "tests"
    ) / "converter_test" / "COCO" / "input" / "fromSuperAnnotate" / "vector_no_name"
    out_path = Path(
        tmpdir
    ) / "empty_name" / "fromSuperAnnotate" / "instance_test_vector"
    sa.export_annotation(
        input_dir, out_path, "COCO", "instance_test_vector", "Vector",
        "instance_segmentation"
    )


def test_upload_annotations_with_template_id(tmpdir):
    tmpdir = Path(tmpdir)
    project_name = "test_templates"
    for project in sa.search_projects(project_name):
        sa.delete_project(project)
    project = sa.create_project(project_name, "test", "Vector")
    sa.upload_images_from_folder_to_project(
        project, "./tests/sample_coco_with_templates"
    )
    input_dir = Path("tests") / "sample_coco_with_templates"
    out_path = Path(
        tmpdir
    ) / "toSuperAnnotate" / "keypoint_detection_multi_template"

    sa.import_annotation(
        input_dir, out_path, "COCO", "sample_coco", "Vector",
        "keypoint_detection"
    )
    sa.upload_annotations_from_folder_to_project(project, out_path)
    image_metadata = sa.get_image_annotations(project_name, "t.png")
    assert image_metadata['annotation_json']['instances'][0]['templateId'] == -1
