from pathlib import Path

import pytest

import superannotate as sa

sa.init(Path.home() / ".superannotate" / "config.json")


@pytest.mark.parametrize(
    "project_type,name,description,from_folder", [
        (
            "Vector", "Example Project test vector", "test vector",
            Path("./tests/sample_project_vector")
        ),
        (
            "Pixel", "Example Project test pixel", "test pixel",
            Path("./tests/sample_project_pixel")
        ),
    ]
)
def test_preannotation_folder_upload_download(
    project_type, name, description, from_folder, tmpdir
):
    projects_found = sa.search_projects(name)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(name, description, project_type)
    sa.upload_images_from_folder_to_project(
        project, from_folder, annotation_status="InProgress"
    )
    old_to_new_classid_conversion = sa.create_annotation_classes_from_classes_json(
        project, from_folder / "classes" / "classes.json"
    )
    sa.upload_preannotations_from_folder_to_project(
        project, from_folder, old_to_new_classid_conversion
    )
    count_in = len(list(from_folder.glob("*.json")))

    images = sa.search_images(project)
    for image in images:
        sa.download_image_preannotations(image, tmpdir)

    count_out = len(list(Path(tmpdir).glob("*.json")))

    assert count_in == count_out
