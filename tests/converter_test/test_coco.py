from pathlib import Path
from glob import glob
import shutil

import superannotate as sa


def coco_vector_instance(tmpdir):
    out_dir = tmpdir / "instance_vector"
    sa.import_annotation_format(
        "tests/converter_test/COCO/input/toSuperAnnotate/instance_segmentation/",
        str(out_dir), "COCO", "instances_test", "Vector",
        "instance_segmentation", "Web"
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


def coco_vector_object(tmpdir):
    out_dir = tmpdir / "object_vector"
    sa.import_annotation_format(
        "tests/converter_test/COCO/input/toSuperAnnotate/instance_segmentation/",
        str(out_dir), "COCO", "instances_test", "Vector", "object_detection",
        "Desktop"
    )


def coco_pixel_instance(tmpdir):
    out_dir = tmpdir / "instance_pixel"
    sa.import_annotation_format(
        "tests/converter_test/COCO/input/toSuperAnnotate/instance_segmentation/",
        str(out_dir), "COCO", "instances_test", "Pixel",
        "instance_segmentation", "Web"
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


def coco_vector_keypoint(tmpdir):
    out_dir = tmpdir / "vector_keypoint"
    sa.import_annotation_format(
        "tests/converter_test/COCO/input/toSuperAnnotate/keypoint_detection/",
        str(out_dir), "COCO", "person_keypoints_test", "Vector",
        "keypoint_detection", "Web"
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


def coco_desktop_object(tmpdir):
    out_dir = tmpdir / "coco_from_desktop"
    final_dir = tmpdir / "coco_to_Web"

    sa.export_annotation_format(
        "tests/converter_test/COCO/input/fromSuperAnnotate/cats_dogs_desktop",
        str(out_dir), "COCO", "object_test", "Vector", "object_detection",
        "Desktop"
    )


def sa_to_coco_to_sa(tmpdir):
    output1 = tmpdir / 'to_coco'
    output2 = tmpdir / 'to_sa'

    sa.export_annotation_format(
        "tests/sample_project_pixel", str(output1), "COCO", "object_test",
        "Pixel", "instance_segmentation", "Web"
    )

    sa.import_annotation_format(
        str(output1), str(output2), "COCO", "object_test", "Pixel",
        "instance_segmentation", "Web", 'image_set'
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


def test_coco(tmpdir):
    coco_vector_instance(tmpdir)
    coco_vector_object(tmpdir)
    coco_pixel_instance(tmpdir)
    coco_vector_keypoint(tmpdir)
    coco_desktop_object(tmpdir)
    sa_to_coco_to_sa(tmpdir)