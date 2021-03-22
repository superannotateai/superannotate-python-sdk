from pathlib import Path

import pytest

import superannotate as sa

PROJECT_NAME_VECTOR = "test attach image urls"
PATH_TO_URLS = Path("./tests/attach_urls.csv")


def test_attach_image_urls():
    projects = sa.search_projects(PROJECT_NAME_VECTOR, return_metadata=True)
    for project in projects:
        sa.delete_project(project)

    project = sa.create_project(PROJECT_NAME_VECTOR, "test", "Vector")

    uploaded, could_not_upload, existing_images = sa.attach_image_urls_to_project(
        project, PATH_TO_URLS
    )

    assert len(uploaded) == 7
    assert len(could_not_upload) == 0
    assert len(existing_images) == 0

    uploaded, could_not_upload, existing_images = sa.attach_image_urls_to_project(
        project, PATH_TO_URLS
    )

    assert len(uploaded) == 2
    assert len(could_not_upload) == 0
    assert len(existing_images) == 5
