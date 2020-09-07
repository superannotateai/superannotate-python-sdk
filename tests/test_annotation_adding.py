from pathlib import Path
import json

import pytest

import superannotate as sa

sa.init(Path.home() / ".superannotate" / "config.json")

PROJECT_NAME = "Example Project test"
PROJECT_DESCRIPTION = "test vector"
PATH_TO_SAMPLE_PROJECT = Path("./tests/sample_project_vector")


def test_add_bbox(tmpdir):
    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(PROJECT_NAME)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(PROJECT_NAME, PROJECT_DESCRIPTION, "Vector")
    sa.upload_images_from_folder_to_project(
        project, PATH_TO_SAMPLE_PROJECT, annotation_status="InProgress"
    )
    sa.create_annotation_classes_from_classes_json(
        project, PATH_TO_SAMPLE_PROJECT / "classes" / "classes.json"
    )
    sa.upload_annotations_from_folder_to_project(
        project, PATH_TO_SAMPLE_PROJECT
    )

    images = sa.search_images(project, "example_image_1")

    annotations = sa.get_image_annotations(images[0])["annotation_json"]

    sa.add_image_annotation_bbox(images[0], [10, 10, 500, 100], "Human")
    annotations_new = sa.get_image_annotations(images[0])["annotation_json"]
    json.dump(annotations_new, open(Path(tmpdir) / "new_anns.json", "w"))

    assert len(annotations_new) == len(annotations) + 1
