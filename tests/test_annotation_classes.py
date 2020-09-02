from pathlib import Path

import superannotate as sa

sa.init(Path.home() / ".superannotate" / "config.json")


def test_annotation_classes():
    project = sa.create_project("test1", "test1", "Vector")
    clss = sa.search_annotation_classes(project)
    assert len(clss) == 0

    ac = sa.create_annotation_class(project, "fff", "#FFFFFF")
    clss = sa.search_annotation_classes(project)
    assert len(clss) == 1

    ac = sa.search_annotation_classes(project, "ff")[0]
    sa.delete_annotation_class(ac)
    clss = sa.search_annotation_classes(project)
    assert len(clss) == 0
    sa.delete_project(project)
