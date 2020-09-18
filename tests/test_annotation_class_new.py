from pathlib import Path
import pytest
import superannotate as sa

sa.init(Path.home() / ".superannotate" / "config.json")

PROJECT_NAME = "test annotation class new"


def test_anntotation_class_new():
    projects = sa.search_projects(PROJECT_NAME, return_metadata=True)
    for project in projects:
        sa.delete_project(project)

    sa.create_project(PROJECT_NAME, "tt", "Vector")

    sa.create_annotation_class(PROJECT_NAME, "tt", "#FFFFFF")

    assert len(sa.search_annotation_classes(PROJECT_NAME)) == 1

    with pytest.raises(sa.SAExistingAnnotationClassNameException):
        sa.create_annotation_class(PROJECT_NAME, "tt", "#FFFFFF")
