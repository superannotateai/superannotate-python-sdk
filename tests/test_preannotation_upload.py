import time
from pathlib import Path

import pytest
import superannotate as sa


@pytest.mark.parametrize(
    "project_type,name,description,from_folder", [
        (
            "Vector", "Example Project test vector preannotation upload",
            "test vector", Path("./tests/sample_project_vector")
        ),
        (
            "Pixel", "Example Project test pixel preannotation upload",
            "test pixel", Path("./tests/sample_project_pixel")
        )
    ]
)
def test_preannotation_folder_upload_download(
    project_type, name, description, from_folder, tmpdir
):
    projects_found = sa.search_projects(name, return_metadata=True)
    for pr in projects_found:
        sa.delete_project(pr)
    time.sleep(2)

    project = sa.create_project(name, description, project_type)
    time.sleep(2)
    sa.upload_images_from_folder_to_project(
        project, from_folder, annotation_status="InProgress"
    )
    sa.create_annotation_classes_from_classes_json(
        project, from_folder / "classes" / "classes.json"
    )
    sa.upload_preannotations_from_folder_to_project(project, from_folder)
    count_in = len(list(from_folder.glob("*.json")))
    time.sleep(2)
    images = sa.search_images(project)
    for image_name in images:
        sa.download_image_preannotations(project, image_name, tmpdir)

    count_out = len(list(Path(tmpdir).glob("*.json")))

    assert count_in == count_out
