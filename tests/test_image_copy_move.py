from pathlib import Path
import json
import io
import time

import pytest

import superannotate as sa

sa.init(Path.home() / ".superannotate" / "config.json")

PROJECT_NAME_CPY = "test image copy"


def test_image_copy(tmpdir):
    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(PROJECT_NAME_CPY)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(PROJECT_NAME_CPY, "test", "Vector")

    sa.upload_image_to_project(
        project,
        "./tests/sample_project_vector/example_image_1.jpg",
        annotation_status="InProgress"
    )
    sa.upload_image_to_project(
        project,
        "./tests/sample_project_vector/example_image_2.jpg",
        annotation_status="InProgress"
    )

    images = sa.search_images(project)
    assert len(images) == 2
    image = images[0]

    sa.copy_image(project, image, project)
    time.sleep(1)
    images = sa.search_images(project)
    assert len(images) == 3

    image = "example_image_1 (1).jpg"
    assert len(sa.search_images(project, image)) == 1
    sa.copy_image(project, image, project)
    time.sleep(1)

    image = "example_image_1 (2).jpg"
    assert len(sa.search_images(project, image)) == 1

    projects_found = sa.search_projects(PROJECT_NAME_CPY + "dif")
    for pr in projects_found:
        sa.delete_project(pr)

    dest_project = sa.create_project(PROJECT_NAME_CPY + "dif", "test", "Vector")
    sa.copy_image(project, image, dest_project)
    time.sleep(1)
    di = sa.search_images(dest_project, image)
    assert len(di) == 1
    assert di[0] == image
