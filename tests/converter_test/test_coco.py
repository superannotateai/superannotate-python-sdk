from pathlib import Path

import pytest

import superannotate as sa


def test_coco_vector_instance(tmpdir):
    input_dir = Path(
        "tests"
    ) / "converter_test" / "COCO" / "input" / "toSuperAnnotate" / "instance_segmentation"
    out_dir = Path(tmpdir) / "instance_vector"
    sa.import_annotation(
        input_dir, out_dir, "COCO", "instances_test", "Vector",
        "instance_segmentation"
    )

    project_name = "coco2sa_vector_instance"

    projects = sa.search_projects(project_name, True)
    if projects:
        sa.delete_project(projects[0])
    project = sa.create_project(project_name, "converter vector", "Vector")

    sa.create_annotation_classes_from_classes_json(
        project, out_dir / "classes" / "classes.json"
    )
    sa.upload_images_from_folder_to_project(project, out_dir)
    sa.upload_annotations_from_folder_to_project(project, out_dir)


def test_coco_vector_object(tmpdir):
    input_dir = Path(
        "tests"
    ) / "converter_test" / "COCO" / "input" / "toSuperAnnotate" / "instance_segmentation"
    out_dir = Path(tmpdir) / "object_vector_desktop"
    sa.import_annotation(
        input_dir, out_dir, "COCO", "instances_test", "Vector",
        "object_detection"
    )


def test_coco_vector_object2(tmpdir):
    input_dir = Path(
        "tests"
    ) / "converter_test" / "COCO" / "input" / "toSuperAnnotate" / "instance_segmentation"
    out_dir = Path(tmpdir) / "object_vector_object_new"
    sa.import_annotation(
        input_dir, out_dir, "COCO", "instances_test", "Vector",
        "object_detection"
    )
    project_name = "coco2sa_vector_object"

    projects = sa.search_projects(project_name, True)
    if projects:
        sa.delete_project(projects[0])
    project = sa.create_project(project_name, "converter vector", "Vector")

    sa.create_annotation_classes_from_classes_json(
        project, out_dir / "classes" / "classes.json"
    )
    sa.upload_images_from_folder_to_project(project, out_dir)
    sa.upload_annotations_from_folder_to_project(project, out_dir)


def test_coco_vector_object_instance(tmpdir):
    input_dir = Path(
        "tests"
    ) / "converter_test" / "COCO" / "input" / "toSuperAnnotate" / "instance_segmentation"
    out_dir = Path(tmpdir) / "object_vector_instance_desktop"
    sa.import_annotation(
        input_dir, out_dir, "COCO", "instances_test", "Vector",
        "instance_segmentation"
    )


def test_coco_pixel_instance(tmpdir):
    input_dir = Path(
        "tests"
    ) / "converter_test" / "COCO" / "input" / "toSuperAnnotate" / "instance_segmentation"
    out_dir = Path(tmpdir) / "instance_pixel"
    sa.import_annotation(
        input_dir, out_dir, "COCO", "instances_test", "Pixel",
        "instance_segmentation"
    )

    project_name = "coco2sa_pixel_instance"

    projects = sa.search_projects(project_name, True)
    if projects:
        sa.delete_project(projects[0])
    project = sa.create_project(project_name, "converter vector", "Pixel")

    sa.create_annotation_classes_from_classes_json(
        project, out_dir / "classes" / "classes.json"
    )
    sa.upload_images_from_folder_to_project(project, out_dir)
    sa.upload_annotations_from_folder_to_project(project, out_dir)


def test_coco_vector_keypoint(tmpdir):
    input_dir = Path(
        "tests"
    ) / "converter_test" / "COCO" / "input" / "toSuperAnnotate" / "keypoint_detection/"
    out_dir = Path(tmpdir) / "vector_keypoint"
    sa.import_annotation(
        input_dir, out_dir, "COCO", "person_keypoints_test", "Vector",
        "keypoint_detection"
    )

    project_name = "coco2sa_keypoint"

    projects = sa.search_projects(project_name, True)
    if projects:
        sa.delete_project(projects[0])
    project = sa.create_project(project_name, "converter vector", "Vector")

    sa.create_annotation_classes_from_classes_json(
        project, out_dir / "classes" / "classes.json"
    )
    sa.upload_images_from_folder_to_project(project, out_dir)
    sa.upload_annotations_from_folder_to_project(project, out_dir)


def test_sa_to_coco_to_sa(tmpdir):
    input_dir = Path("tests") / "sample_project_pixel"
    output1 = Path(tmpdir) / 'to_coco'
    output2 = Path(tmpdir) / 'to_sa'

    sa.export_annotation(
        input_dir, output1, "COCO", "object_test", "Pixel",
        "instance_segmentation"
    )

    sa.import_annotation(
        output1, output2, "COCO", "object_test", "Pixel",
        "instance_segmentation", 'image_set'
    )

    project_name = 'coco_pipeline_new'
    project = sa.search_projects(project_name, return_metadata=True)
    for pr in project:
        sa.delete_project(pr)

    project = sa.create_project(project_name, 'test_instane', 'Pixel')
    sa.upload_images_from_folder_to_project(project, output2)
    sa.create_annotation_classes_from_classes_json(
        project, output2 / "classes" / "classes.json"
    )
    sa.upload_annotations_from_folder_to_project(project, output2)
