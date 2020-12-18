from pathlib import Path
import time

import pytest

import superannotate as sa

PROJECT_NAME_VECTOR = "test assign images"


def test_assign_images(tmpdir):
    tmpdir = Path(tmpdir)

    projects = sa.search_projects(PROJECT_NAME_VECTOR, return_metadata=True)
    for project in projects:
        sa.delete_project(project)

    project = sa.create_project(PROJECT_NAME_VECTOR, "test", "Vector")
    email = sa.get_team_metadata()["users"][0]["email"]
    sa.share_project(project, email, "QA")

    sa.upload_images_from_folder_to_project(
        project, "./tests/sample_project_vector"
    )

    sa.assign_images(
        project, ["example_image_1.jpg", "example_image_2.jpg"], email
    )

    time.sleep(1)
    im1_metadata = sa.get_image_metadata(project, "example_image_1.jpg")
    im2_metadata = sa.get_image_metadata(project, "example_image_2.jpg")

    assert im1_metadata["qa_id"] == email
    assert im2_metadata["qa_id"] == email

    sa.unshare_project(project, email)

    time.sleep(1)

    im1_metadata = sa.get_image_metadata(project, "example_image_1.jpg")
    im2_metadata = sa.get_image_metadata(project, "example_image_2.jpg")

    assert im1_metadata["qa_id"] is None
    assert im2_metadata["qa_id"] is None
    assert im1_metadata["annotator_id"] is None
    assert im2_metadata["annotator_id"] is None

    sa.share_project(project, email, "Annotator")

    sa.assign_images(
        project, ["example_image_1.jpg", "example_image_2.jpg"], email
    )

    time.sleep(1)
    im1_metadata = sa.get_image_metadata(project, "example_image_1.jpg")
    im2_metadata = sa.get_image_metadata(project, "example_image_2.jpg")

    assert im1_metadata["annotator_id"] == email
    assert im2_metadata["annotator_id"] == email
    assert im1_metadata["qa_id"] is None
    assert im2_metadata["qa_id"] is None
