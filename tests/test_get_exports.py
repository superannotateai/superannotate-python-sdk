from pathlib import Path
import json

import pytest

import superannotate as sa

PROJECT_NAME = "test_get_exports"


def test_get_exports(tmpdir):
    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(PROJECT_NAME)
    for pr in projects_found:
        sa.delete_project(pr)
    project = sa.create_project(PROJECT_NAME, "gg", "Vector")
    sa.upload_images_from_folder_to_project(
        project,
        "./tests/sample_project_vector/", annotation_status="QualityCheck"
    )
    sa.create_annotation_classes_from_classes_json(
        project,
        "./tests/sample_project_vector/classes/classes.json",
    )
    sa.upload_annotations_from_folder_to_project(
        project,
        "./tests/sample_project_vector/",
    )
    export = sa.prepare_export(project)
    sa.download_export(project, export, tmpdir)
    js = list(tmpdir.glob("*.json"))

    assert len(js) == 4
