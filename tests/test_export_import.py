from pathlib import Path
import json

import pytest

import superannotate as sa

sa.init(Path.home() / ".superannotate" / "config.json")

PROJECT_NAME = "test export import"
PROJECT_FOLDER = Path("./tests/sample_project_vector")


def test_basic_export(tmpdir):
    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(PROJECT_NAME)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(PROJECT_NAME, "t", "Vector")
    sa.upload_images_from_folder_to_project(
        project, PROJECT_FOLDER, annotation_status="InProgress"
    )
    len_orig = len(sa.search_images(project))

    sa.create_annotation_classes_from_classes_json(
        project, PROJECT_FOLDER / "classes" / "classes.json"
    )
    sa.upload_annotations_from_folder_to_project(project, PROJECT_FOLDER)

    export = sa.prepare_export(project, include_fuse=True)

    sa.download_export(project, export, tmpdir)

    project_new = sa.create_project(PROJECT_NAME + " import", "f", "Vector")
    sa.upload_images_from_folder_to_project(
        project_new, tmpdir, annotation_status="InProgress"
    )
    len_new = len(sa.search_images(project_new))

    assert len_new == len_orig
