from pathlib import Path
import os

import pytest

import superannotate as sa

sa.init(Path.home() / ".superannotate" / "config.json")


@pytest.mark.skipif(
    "AO_TEST_LEVEL" not in os.environ or
    os.environ["AO_TEST_LEVEL"] != "stress",
    reason="Requires env variable to be set"
)
def test_upload_stress():
    project = sa.create_project("test_test_15", "hk", 1)
    sa.create_annotation_classes_from_classes_json(
        project, "tests/sample_project_vector/classes/classes.json"
    )

    sa.upload_images_from_folder_to_project(
        project,
        "/media/disc_drive/datasets/COCO/test2017",
        annotation_status=3
    )
    count = sa.get_project_image_count(project)
    assert count == 40670

    # sa.delete_project(project)
