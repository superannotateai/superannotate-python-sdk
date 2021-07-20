from pathlib import Path
import time

import pytest

import superannotate as sa

PROJECT_NAME1 = "test pin image1"
PROJECT_NAME2 = "test pin image2"
FOLDER2 = "test folder2"


def test_pin_image(tmpdir):
    tmpdir = Path(tmpdir)

    projects = sa.search_projects(PROJECT_NAME1, return_metadata=True)
    for project in projects:
        sa.delete_project(project)

    time.sleep(2)

    project = sa.create_project(PROJECT_NAME1, "test", "Vector")
    time.sleep(2)
    sa.upload_images_from_folder_to_project(
        project,
        "./tests/sample_project_vector",
        annotation_status="QualityCheck"
    )
    time.sleep(2)

    img_metadata0 = sa.get_image_metadata(project, "example_image_1.jpg")
    assert img_metadata0["is_pinned"] == 0

    sa.pin_image(project, "example_image_1.jpg")
    time.sleep(1)

    img_metadata = sa.get_image_metadata(project, "example_image_1.jpg")
    assert img_metadata["is_pinned"] == 1

    sa.pin_image(project, "example_image_1.jpg", True)
    time.sleep(1)
    img_metadata = sa.get_image_metadata(project, "example_image_1.jpg")
    assert img_metadata["is_pinned"] == 1

    sa.pin_image(project, "example_image_1.jpg", False)
    time.sleep(1)

    img_metadata = sa.get_image_metadata(project, "example_image_1.jpg")
    assert img_metadata["is_pinned"] == 0

    del img_metadata["updatedAt"]
    del img_metadata0["updatedAt"]

    assert img_metadata == img_metadata0


def test_pin_image_in_folder(tmpdir):
    tmpdir = Path(tmpdir)

    projects = sa.search_projects(PROJECT_NAME2, return_metadata=True)
    for project in projects:
        sa.delete_project(project)
    time.sleep(2)

    project = sa.create_project(PROJECT_NAME2, "test", "Vector")
    time.sleep(2)
    sa.create_folder(project, FOLDER2)
    time.sleep(2)

    project_folder = project["name"] + "/" + FOLDER2
    sa.upload_images_from_folder_to_project(
        project_folder,
        "./tests/sample_project_vector",
        annotation_status="QualityCheck"
    )
    time.sleep(2)

    img_metadata0 = sa.get_image_metadata(project_folder, "example_image_1.jpg")
    assert img_metadata0["is_pinned"] == 0

    sa.pin_image(project_folder, "example_image_1.jpg")
    time.sleep(1)

    img_metadata = sa.get_image_metadata(project_folder, "example_image_1.jpg")
    assert img_metadata["is_pinned"] == 1

    sa.pin_image(project_folder, "example_image_1.jpg", True)
    time.sleep(1)
    img_metadata = sa.get_image_metadata(project_folder, "example_image_1.jpg")
    assert img_metadata["is_pinned"] == 1

    sa.pin_image(project_folder, "example_image_1.jpg", False)
    time.sleep(1)

    img_metadata = sa.get_image_metadata(project_folder, "example_image_1.jpg")
    assert img_metadata["is_pinned"] == 0

    del img_metadata["updatedAt"]
    del img_metadata0["updatedAt"]

    assert img_metadata == img_metadata0
