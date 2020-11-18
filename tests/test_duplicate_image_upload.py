from pathlib import Path
import time

import pytest

import superannotate as sa

PROJECT_NAME_VECTOR = "test duplicate upload images"


def test_duplicate_upload_images(tmpdir):
    tmpdir = Path(tmpdir)

    projects = sa.search_projects(PROJECT_NAME_VECTOR, return_metadata=True)
    for project in projects:
        sa.delete_project(project)

    project = sa.create_project(PROJECT_NAME_VECTOR, "test", "Vector")

    uploads = sa.upload_images_from_folder_to_project(
        project, "./tests/sample_project_vector"
    )

    assert len(uploads[0]) == 4
    assert len(uploads[1]) == 0
    assert len(uploads[2]) == 0

    uploads = sa.upload_images_to_project(
        project, ["./tests/sample_project_vector/dd.jpg"]
    )

    assert len(uploads[0]) == 0
    assert len(uploads[1]) == 1
    assert len(uploads[2]) == 0

    uploads = sa.upload_images_from_folder_to_project(
        project, "./tests/sample_project_vector"
    )

    assert len(uploads[0]) == 0
    assert len(uploads[1]) == 0
    assert len(uploads[2]) == 4
