import time
from pathlib import Path
import pytest
import superannotate as sa
from .test_assign_images import safe_create_project


def test_anntotation_class_new():

    PROJECT_NAME = "test_anntotation_class_new"
    safe_create_project(PROJECT_NAME,'test','Vector')
    time.sleep(2)
    sa.create_annotation_class(PROJECT_NAME, "tt", "#FFFFFF")

    time.sleep(2)

    assert len(sa.search_annotation_classes(PROJECT_NAME)) == 1

    sa.create_annotation_class(PROJECT_NAME, "tt", "#FFFFFF")
    time.sleep(2)
    assert len(sa.search_annotation_classes(PROJECT_NAME)) == 1


def test_anntotation_class_new_json():

    PROJECT_NAME_JSON = "test_anntotation_class_new_json"
    safe_create_project(PROJECT_NAME_JSON,'test','Vector')

    sa.create_annotation_classes_from_classes_json(
        PROJECT_NAME_JSON, "./tests/sample_project_vector/classes/classes.json"
    )

    time.sleep(2)
    assert len(sa.search_annotation_classes(PROJECT_NAME_JSON)) == 4

    sa.create_annotation_classes_from_classes_json(
        PROJECT_NAME_JSON, "./tests/sample_project_vector/classes/classes.json"
    )
    time.sleep(2)

    assert len(sa.search_annotation_classes(PROJECT_NAME_JSON)) == 4
