import os
import time
from pathlib import Path

import pytest
import superannotate as sa

PROJECT_NAME = "test stress upload"


@pytest.mark.skipif(
    "SA_STRESS_TESTS" not in os.environ,
    reason="Requires env variable to be set"
)
@pytest.mark.timeout(3 * 3600)
def test_upload_stress(tmpdir):
    tmpdir = Path(tmpdir)

    projects = sa.search_projects(PROJECT_NAME, return_metadata=True)
    for project in projects:
        sa.delete_project(project)
    project = sa.create_project(PROJECT_NAME, "hk", "Vector")

    sa.create_annotation_classes_from_classes_json(
        project, "tests/sample_project_vector/classes/classes.json"
    )

    sa.upload_images_from_folder_to_project(
        project,
        "/media/disc_drive/datasets/COCO/test2017",
        annotation_status="QualityCheck"
    )
    time.sleep(60)
    count = sa.get_project_image_count(project)
    assert count == 40670

    # export = sa.prepare_export(project)
    # sa.download_export(project, export, tmpdir)

    # count_in_project = sa.get_project_image_count(project)
    # count_in_folder = len(list(Path(tmpdir).glob("*.jpg")))

    # assert count_in_project == count_in_folder
