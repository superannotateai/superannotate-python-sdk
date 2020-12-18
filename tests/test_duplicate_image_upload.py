from pathlib import Path

import pytest

import superannotate as sa

PROJECT_NAME_VECTOR = "test duplicate upload images"


def test_duplicate_upload_images(tmpdir):
    tmpdir = Path(tmpdir)

    projects = sa.search_projects(PROJECT_NAME_VECTOR, return_metadata=True)
    for project in projects:
        sa.delete_project(project)

    project = sa.create_project(PROJECT_NAME_VECTOR, "test", "Vector")

    uploaded, could_not_upload, existing_images = sa.upload_images_from_folder_to_project(
        project, "./tests/sample_project_vector"
    )

    assert len(uploaded) == 4
    assert len(could_not_upload) == 0
    assert len(existing_images) == 0

    uploaded, could_not_upload, existing_images = sa.upload_images_to_project(
        project, ["./tests/sample_project_vector/dd.jpg"]
    )

    assert len(uploaded) == 0
    assert len(could_not_upload) == 1
    assert len(existing_images) == 0

    uploaded, could_not_upload, existing_images = sa.upload_images_from_folder_to_project(
        project, "./tests/sample_project_vector"
    )

    assert len(uploaded) == 0
    assert len(could_not_upload) == 0
    assert len(existing_images) == 4
