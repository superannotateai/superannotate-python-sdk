from pathlib import Path
import filecmp

import pytest

import superannotate as sa

sa.init(Path.home() / ".superannotate" / "config.json")

PROJECT_NAME = "testing_1419"


@pytest.mark.parametrize(
    "project_type,name,description,from_folder", [
        (
            1, "Example Project test", "test vector",
            Path("./tests/sample_project_vector")
        ),
        (
            2, "Example Project test", "test pixe",
            Path("./tests/sample_project_pixel")
        )
    ]
)
def test_annotation_download_upload(
    project_type, name, description, from_folder, tmpdir
):
    team = sa.get_default_team()
    projects = sa.search_projects(team, name)
    for project in projects:
        sa.delete_project(project)
    project = sa.create_project(team, name, description, project_type)
    sa.upload_images_from_folder_to_project(
        project, from_folder, annotation_status=1
    )
    sa.create_annotation_classes_from_classes_json(
        project, from_folder / "classes" / "classes.json"
    )
    sa.upload_annotations_from_folder_to_project(project, from_folder)
    image = sa.search_images(project)[3]
    sa.download_image_annotations(image, tmpdir)
    anns_json_in_folder = list(Path(tmpdir).glob("*.json"))
    anns_mask_in_folder = list(Path(tmpdir).glob("*.png"))
    assert len(anns_json_in_folder) == 1
    assert len(anns_mask_in_folder) == project_type - 1

    input_annotation_paths = sa.image_path_to_annotation_paths(
        from_folder / image["name"], project_type
    )
    assert filecmp.cmp(
        input_annotation_paths[0], anns_json_in_folder[0], shallow=False
    )
    if project_type == 2:
        assert filecmp.cmp(
            input_annotation_paths[1], anns_mask_in_folder[0], shallow=False
        )
    # sa.download_image_preannotations(image, tmpdir)
