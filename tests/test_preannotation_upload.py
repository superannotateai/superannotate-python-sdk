from pathlib import Path

import pytest

import superannotate as sa

sa.init(Path.home() / ".superannotate" / "config.json")


@pytest.mark.parametrize(
    "project_type,name,description,from_folder", [
        (
            1, "Example Project test", "test vector",
            Path("./tests/sample_project_vector")
        ),
        (
            2, "Example Project test", "test pixel",
            Path("./tests/sample_project_pixel")
        ),
    ]
)
def test_preannotation_folder_upload_download(
    project_type, name, description, from_folder, tmpdir
):
    if project_type == 2:  # skip until implemented
        return
    team = sa.get_default_team()
    projects_found = sa.search_projects(team, name)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(team, name, description, project_type)
    sa.upload_images_from_folder_to_project(project, from_folder, annotation_status=2)
    sa.upload_preannotations_from_folder(project, from_folder)
    count_in = len(list(from_folder.glob("*.json")))

    images = sa.search_images(project)
    for image in images:
        sa.download_image_preannotations(image, tmpdir)

    count_out = len(list(Path(tmpdir).glob("*.json")))

    assert count_in == count_out
