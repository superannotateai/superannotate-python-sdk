from pathlib import Path
import subprocess
import time

import pytest

import superannotate as sa


@pytest.mark.parametrize(
    "project_type,name,description,from_folder", [
        (
            "Vector", "Example Project test0 vector preannotation cli upload",
            "test vector", Path("./tests/sample_project_vector")
        ),
        (
            "Pixel", "Example Project test0 pixel preannotation cli upload",
            "test pixel", Path("./tests/sample_project_pixel")
        )
    ]
)
def test_preannotation_folder_upload_download_cli(
    project_type, name, description, from_folder, tmpdir
):
    projects_found = sa.search_projects(name, return_metadata=True)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(name, description, project_type)
    sa.upload_images_from_folder_to_project(
        project, from_folder, annotation_status="InProgress"
    )
    sa.create_annotation_classes_from_classes_json(
        project, from_folder / "classes" / "classes.json"
    )
    subprocess.run(
        [
            f"superannotate upload-preannotations --project '{name}' --folder '{from_folder}'"
        ],
        check=True,
        shell=True
    )
    time.sleep(5)
    count_in = len(list(from_folder.glob("*.json")))

    images = sa.search_images(project)
    for image_name in images:
        sa.download_image_preannotations(project, image_name, tmpdir)

    count_out = len(list(Path(tmpdir).glob("*.json")))

    assert count_in == count_out


def test_annotation_folder_upload_download_cli_vector_COCO(tmpdir):
    project_type = "Vector"
    name = "Example Project test vector2 annotation cli upload coco vector"
    description = "test"
    from_folder = "./tests/converter_test/COCO/input/toSuperAnnotate/keypoint_detection"
    task = "keypoint_detection"
    dataset_name = "person_keypoints_test"

    projects_found = sa.search_projects(name, return_metadata=True)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(name, description, project_type)
    sa.upload_images_from_folder_to_project(
        project, from_folder, annotation_status="InProgress"
    )
    # sa.create_annotation_classes_from_classes_json(
    #     project, from_folder / "classes" / "classes.json"
    # )
    subprocess.run(
        [
            f"superannotate upload-annotations --project '{name}' --folder '{from_folder}' --format COCO --task {task} --dataset-name {dataset_name}"
        ],
        check=True,
        shell=True
    )
    # time.sleep(5)
    # count_in = len(list(from_folder.glob("*.json")))

    # images = sa.search_images(project)
    # for image_name in images:
    #     sa.download_image_preannotations(project, image_name, tmpdir)

    # count_out = len(list(Path(tmpdir).glob("*.json")))

    # assert count_in == count_out


def test_preannotation_folder_upload_download_cli_vector_COCO(tmpdir):
    project_type = "Vector"
    name = "Example Project test vector2 preannotation cli upload coco vector"
    description = "test"
    from_folder = "./tests/converter_test/COCO/input/toSuperAnnotate/keypoint_detection"
    task = "keypoint_detection"
    dataset_name = "person_keypoints_test"

    projects_found = sa.search_projects(name, return_metadata=True)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(name, description, project_type)
    sa.upload_images_from_folder_to_project(
        project, from_folder, annotation_status="InProgress"
    )
    # sa.create_annotation_classes_from_classes_json(
    #     project, from_folder / "classes" / "classes.json"
    # )
    subprocess.run(
        [
            f"superannotate upload-preannotations --project '{name}' --folder '{from_folder}' --format COCO --task {task} --dataset-name {dataset_name}"
        ],
        check=True,
        shell=True
    )
    # time.sleep(5)
    # count_in = len(list(from_folder.glob("*.json")))

    # images = sa.search_images(project)
    # for image_name in images:
    #     sa.download_image_preannotations(project, image_name, tmpdir)

    # count_out = len(list(Path(tmpdir).glob("*.json")))

    # assert count_in == count_out


def test_preannotation_folder_upload_download_cli_vector_object_COCO(tmpdir):
    project_type = "Vector"
    name = "Example Project test vector1 preannotation cli upload coco object vector"
    description = "test"
    from_folder = "./tests/converter_test/COCO/input/toSuperAnnotate/instance_segmentation"
    task = "instance_segmentation"
    dataset_name = "instances_test"

    projects_found = sa.search_projects(name, return_metadata=True)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(name, description, project_type)
    sa.upload_images_from_folder_to_project(
        project, from_folder, annotation_status="InProgress"
    )
    # sa.create_annotation_classes_from_classes_json(
    #     project, from_folder / "classes" / "classes.json"
    # )
    subprocess.run(
        [
            f"superannotate upload-preannotations --project '{name}' --folder '{from_folder}' --format COCO --task {task} --dataset-name {dataset_name}"
        ],
        check=True,
        shell=True
    )


def test_preannotation_folder_upload_download_cli_pixel_object_COCO(tmpdir):
    project_type = "Pixel"
    name = "Example Project test pixel1 preannotation cli upload coco object pixel"
    description = "test"
    from_folder = "./tests/converter_test/COCO/input/toSuperAnnotate/panoptic_segmentation"
    task = "panoptic_segmentation"
    dataset_name = "panoptic_test"

    projects_found = sa.search_projects(name, return_metadata=True)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(name, description, project_type)
    sa.upload_images_from_folder_to_project(
        project, from_folder, annotation_status="InProgress"
    )
    # sa.create_annotation_classes_from_classes_json(
    #     project, from_folder / "classes" / "classes.json"
    # )
    subprocess.run(
        [
            f"superannotate upload-preannotations --project '{name}' --folder '{from_folder}' --format COCO --task {task} --dataset-name {dataset_name}"
        ],
        check=True,
        shell=True
    )
