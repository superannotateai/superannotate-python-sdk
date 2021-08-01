import time
from pathlib import Path
from .test_assign_images import safe_create_project
import superannotate as sa

sa.init(Path.home() / ".superannotate" / "config.json")



def test_annotation_classes():
    PROJECT_NAME = "test_annotation_classes"

    project = safe_create_project(PROJECT_NAME,"tt","Vector")
    time.sleep(2)
    clss = sa.search_annotation_classes(project)
    assert len(clss) == 0

    ac = sa.create_annotation_class(project, "fff", "#FFFFFF")
    time.sleep(1)
    clss = sa.search_annotation_classes(project)
    assert len(clss) == 1

    ac = sa.search_annotation_classes(project, "ff")[0]
    time.sleep(1)
    sa.delete_annotation_class(project, ac)
    time.sleep(1)
    clss = sa.search_annotation_classes(project)
    assert len(clss) == 0
    sa.delete_project(project)
