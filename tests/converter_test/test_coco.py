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

    # project_name = "coco2sa_vector_object"

    # projects = sa.search_projects(project_name, True)
    # if projects:
    #     sa.delete_project(projects[0])
    # project = sa.create_project(project_name, "converter vector", "Vector")

    # sa.create_annotation_classes_from_classes_json(
    #     project, out_dir / "classes" / "classes.json"
    # )
    # sa.upload_images_from_folder_to_project(project, out_dir)
    # sa.upload_annotations_from_folder_to_project(project, out_dir)


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

    image_list = glob(str(out_dir / 'train_set' / '*.jpg'))

    for image in image_list:
        shutil.copy(image, out_dir / Path(image).name)
    shutil.rmtree(out_dir / 'train_set')

    sa.import_annotation_format(
        str(out_dir), str(final_dir), "COCO", "object_test_train", "Vector",
        "object_detection", "Web"
    )

    project_name = "coco2sa_object_pipline"

    projects = sa.search_projects(project_name, True)
    if projects:
        sa.delete_project(projects[0])
    project = sa.create_project(project_name, "converter vector", "Vector")

    sa.create_annotation_classes_from_classes_json(
        project, final_dir / "classes" / "classes.json"
    )
    sa.upload_images_from_folder_to_project(project, final_dir)
    sa.upload_annotations_from_folder_to_project(project, final_dir)


def test_coco(tmpdir):
    coco_vector_instance(tmpdir)
    coco_vector_object(tmpdir)
    coco_pixel_instance(tmpdir)
    coco_vector_keypoint(tmpdir)
    coco_desktop_object(tmpdir)