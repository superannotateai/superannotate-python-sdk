from pathlib import Path
import time

import pytest

import superannotate as sa

PROJECT_NAME1 = "test pin image"


def test_pin_image(tmpdir):
    tmpdir = Path(tmpdir)

    projects = sa.search_projects(PROJECT_NAME1, return_metadata=True)
    for project in projects:
        sa.delete_project(project)

    project = sa.create_project(PROJECT_NAME1, "test", "Vector")

    sa.upload_images_from_folder_to_project(
        project,
        "./tests/sample_project_vector",
        annotation_status="QualityCheck"
    )

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

    img_metadata = sa.get_image_metadata(project, "example_image_1.jpg")
    time.sleep(1)
    assert img_metadata["is_pinned"] == 0

    del img_metadata["updatedAt"]
    del img_metadata0["updatedAt"]

    assert img_metadata == img_metadata0
