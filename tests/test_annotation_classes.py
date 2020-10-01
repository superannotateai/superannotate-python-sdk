from pathlib import Path

import superannotate as sa

sa.init(Path.home() / ".superannotate" / "config.json")

PROJECT_NAME = "test annotation classes"


def test_annotation_classes():
    projects = sa.search_projects(PROJECT_NAME, return_metadata=True)
    for project in projects:
        sa.delete_project(project)
    project = sa.create_project(PROJECT_NAME, "test1", "Vector")
    clss = sa.search_annotation_classes(project)
    assert len(clss) == 0

    ac = sa.create_annotation_class(project, "fff", "#FFFFFF")
    clss = sa.search_annotation_classes(project)
    assert len(clss) == 1

    ac = sa.search_annotation_classes(project, "ff")[0]
    sa.delete_annotation_class(project, ac)
    clss = sa.search_annotation_classes(project)
    assert len(clss) == 0
    sa.delete_project(project)
