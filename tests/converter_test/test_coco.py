from pathlib import Path
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

    return 0


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
    return 0


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

    return 0


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

    return 0


def test_coco(tmpdir):
    assert coco_vector_instance(tmpdir) == 0
    assert coco_vector_object(tmpdir) == 0
    assert coco_pixel_instance(tmpdir) == 0
    assert coco_vector_keypoint(tmpdir) == 0
