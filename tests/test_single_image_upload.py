from pathlib import Path
import json
import io

import pytest

import superannotate as sa

PROJECT_NAME = "test single image upload 1"
PROJECT_NAME_S3 = "test single image upload s3 2"
PROJECT_NAME_S3_CHANGE_NAME = "test single image upload s3 change name 3"
PROJECT_NAME_BYTES = "test single image upload bytes 4"


def test_single_image_upload(tmpdir):
    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(PROJECT_NAME, return_metadata=True)
    print(projects_found)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(PROJECT_NAME, "test", "Vector")

    sa.upload_image_to_project(
        project,
        "./tests/sample_project_vector/example_image_1.jpg",
        annotation_status="InProgress"
    )

    images = sa.search_images(project)
    assert len(images) == 1
    image = images[0]
    assert sa.annotation_status_int_to_str(
        sa.get_image_metadata(project, image)["annotation_status"]
    ) == "InProgress"
    assert image == "example_image_1.jpg"


def test_single_image_upload_s3(tmpdir):
    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(PROJECT_NAME_S3, return_metadata=True)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(PROJECT_NAME_S3, "test", "Vector")

    sa.upload_image_to_project(
        project,
        "sample_project_vector/example_image_1.jpg",
        annotation_status="InProgress",
        from_s3_bucket="superannotate-python-sdk-test"
    )

    images = sa.search_images(project)
    assert len(images) == 1
    image = images[0]
    assert sa.annotation_status_int_to_str(
        sa.get_image_metadata(project, image)["annotation_status"]
    ) == "InProgress"


def test_single_image_upload_s3_change_name(tmpdir):
    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(
        PROJECT_NAME_S3_CHANGE_NAME, return_metadata=True
    )
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(PROJECT_NAME_S3_CHANGE_NAME, "test", "Vector")

    sa.upload_image_to_project(
        project,
        "sample_project_vector/example_image_1.jpg",
        image_name="rr.jpg",
        annotation_status="InProgress",
        from_s3_bucket="superannotate-python-sdk-test"
    )

    images = sa.search_images(project)
    assert len(images) == 1
    image = images[0]
    assert sa.annotation_status_int_to_str(
        sa.get_image_metadata(project, image)["annotation_status"]
    ) == "InProgress"
    assert image == "rr.jpg"


def test_single_image_upload_bytesio(tmpdir):
    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(
        PROJECT_NAME_BYTES, return_metadata=True
    )
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(PROJECT_NAME_BYTES, "test", "Vector")

    with open("./tests/sample_project_vector/example_image_1.jpg", "rb") as f:
        img = io.BytesIO(f.read())
    try:
        sa.upload_image_to_project(project, img, annotation_status="InProgress")
    except sa.SABaseException as e:
        assert e.message == "Image name img_name should be set if img is not Pathlike"
    else:
        assert False

    sa.upload_image_to_project(
        project, img, image_name="rr.jpg", annotation_status="InProgress"
    )
    images = sa.search_images(project)
    assert len(images) == 1
    image = images[0]
    assert sa.annotation_status_int_to_str(
        sa.get_image_metadata(project, image)["annotation_status"]
    ) == "InProgress"
    assert image == "rr.jpg"
