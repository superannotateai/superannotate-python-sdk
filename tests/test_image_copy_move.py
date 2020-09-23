from pathlib import Path
import json
import io
import time

import pytest

import superannotate as sa

sa.init(Path.home() / ".superannotate" / "config.json")

PROJECT_NAME_CPY = "test image copy"
PROJECT_NAME_CPY_MULT = "test image copy mult"
PROJECT_NAME_MOVE = "test image move"


def test_image_copy_mult(tmpdir):
    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(
        PROJECT_NAME_CPY_MULT, return_metadata=True, exact_match=True
    )
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(PROJECT_NAME_CPY_MULT, "test", "Vector")

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

    for _ in range(3):
        sa.copy_image(project, image, project)
    assert len(sa.search_images(project)) == 5
    images = sa.search_images(project)
    for i in range(3):
        assert f"example_image_1_({i+1}).jpg" in images


def test_image_copy(tmpdir):
    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(
        PROJECT_NAME_CPY, return_metadata=True, exact_match=True
    )
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
    images = sa.search_images(project)
    assert len(images) == 3

    image = "example_image_1_(1).jpg"
    assert len(sa.search_images(project, image)) == 1
    sa.copy_image(project, image, project)

    image = "example_image_1_(2).jpg"
    assert len(sa.search_images(project, image)) == 1

    projects_found = sa.search_projects(
        PROJECT_NAME_CPY + "dif", return_metadata=True, exact_match=True
    )
    for pr in projects_found:
        sa.delete_project(pr)

    dest_project = sa.create_project(PROJECT_NAME_CPY + "dif", "test", "Vector")
    sa.copy_image(project, image, dest_project)
    di = sa.search_images(dest_project, image)
    assert len(di) == 1
    assert di[0] == image


def test_image_move(tmpdir):
    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(
        PROJECT_NAME_MOVE, return_metadata=True, exact_match=True
    )
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(PROJECT_NAME_MOVE, "test", "Vector")

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
    try:
        sa.move_image(project, image, project)
    except sa.SABaseException as e:
        assert e.message == "Cannot move image if source_project == destination_project."
    else:
        assert False

    projects_found = sa.search_projects(
        PROJECT_NAME_MOVE + "dif", return_metadata=True, exact_match=True
    )
    for pr in projects_found:
        sa.delete_project(pr)

    dest_project = sa.create_project(
        PROJECT_NAME_MOVE + "dif", "test", "Vector"
    )
    sa.move_image(project, image, dest_project)
    di = sa.search_images(dest_project, image)
    assert len(di) == 1
    assert di[0] == image

    si = sa.search_images(project, image)
    assert len(si) == 0

    si = sa.search_images(project)
    assert len(si) == 1
