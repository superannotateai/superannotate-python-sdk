import time
from pathlib import Path
import io

import superannotate as sa
from .test_assign_images import safe_create_project
PROJECT_NAME = "test single image upload 1"
PROJECT_NAME_S3 = "test single image upload s3 2"
PROJECT_NAME_S3_CHANGE_NAME = "test single image upload s3 change name 3"
PROJECT_NAME_BYTES = "test single image upload bytes 4"


def test_single_image_upload(tmpdir):
    project = safe_create_project(PROJECT_NAME)

    sa.upload_image_to_project(
        project,
        "./tests/sample_project_vector/example_image_1.jpg",
        annotation_status="InProgress"
    )

    time.sleep(2)
    images = sa.search_images(project)
    assert len(images) == 1
    image = images[0]
    assert sa.get_image_metadata(project,
                                 image)["annotation_status"] == "InProgress"
    assert image == "example_image_1.jpg"


def test_single_image_upload_s3(tmpdir):
    project = safe_create_project(PROJECT_NAME_S3)

    sa.upload_image_to_project(
        project,
        "sample_project_vector/example_image_1.jpg",
        annotation_status="InProgress",
        from_s3_bucket="superannotate-python-sdk-test"
    )
    time.sleep(2)

    images = sa.search_images(project)
    assert len(images) == 1
    image = images[0]
    assert sa.get_image_metadata(project,
                                 image)["annotation_status"] == "InProgress"


def test_single_image_upload_s3_change_name(tmpdir):
    project = safe_create_project(PROJECT_NAME_S3_CHANGE_NAME)

    sa.upload_image_to_project(
        project,
        "sample_project_vector/example_image_1.jpg",
        image_name="rr.jpg",
        annotation_status="InProgress",
        from_s3_bucket="superannotate-python-sdk-test"
    )

    time.sleep(2)

    images = sa.search_images(project)
    assert len(images) == 1
    image = images[0]
    assert sa.get_image_metadata(project,
                                 image)["annotation_status"] == "InProgress"
    assert image == "rr.jpg"


def test_single_image_upload_bytesio(tmpdir):
    project = safe_create_project(PROJECT_NAME_BYTES)

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
    time.sleep(2)
    images = sa.search_images(project)
    assert len(images) == 1
    image = images[0]
    assert sa.get_image_metadata(project,
                                 image)["annotation_status"] == "InProgress"
    assert image == "rr.jpg"
