from pathlib import Path
import pytest
import superannotate as sa

PROJECT_NAME = "test annotation class new 1"
PROJECT_NAME_JSON = "test annotation class new json 2"


def test_anntotation_class_new():
    projects = sa.search_projects(PROJECT_NAME, return_metadata=True)
    for project in projects:
        sa.delete_project(project)

    sa.create_project(PROJECT_NAME, "tt", "Vector")

    sa.create_annotation_class(PROJECT_NAME, "tt", "#FFFFFF")

    assert len(sa.search_annotation_classes(PROJECT_NAME)) == 1

    sa.create_annotation_class(PROJECT_NAME, "tt", "#FFFFFF")

    assert len(sa.search_annotation_classes(PROJECT_NAME)) == 1


def test_anntotation_class_new_json():
    projects = sa.search_projects(PROJECT_NAME_JSON, return_metadata=True)
    for project in projects:
        sa.delete_project(project)

    sa.create_project(PROJECT_NAME_JSON, "tt", "Vector")

    sa.create_annotation_classes_from_classes_json(
        PROJECT_NAME_JSON, "./tests/sample_project_vector/classes/classes.json"
    )

    assert len(sa.search_annotation_classes(PROJECT_NAME_JSON)) == 3

    sa.create_annotation_classes_from_classes_json(
        PROJECT_NAME_JSON, "./tests/sample_project_vector/classes/classes.json"
    )

    assert len(sa.search_annotation_classes(PROJECT_NAME_JSON)) == 3
