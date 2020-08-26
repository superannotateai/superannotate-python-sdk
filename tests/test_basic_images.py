from pathlib import Path
import json

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
def test_basic_images(project_type, name, description, from_folder, tmpdir):
    tmpdir = Path(tmpdir)
    team = sa.get_default_team()

    projects_found = sa.search_projects(team, name)
    for pr in projects_found:
        sa.delete_project(pr)

    projects_found = sa.search_projects(team, name)
    project = sa.create_project(team, name, description, project_type)
    sa.upload_images_from_folder_to_project(
        project, from_folder, annotation_status=1
    )
    old_to_new_classes_conversion = sa.create_annotation_classes_from_classes_json(
        project, from_folder / "classes" / "classes.json"
    )
    images = sa.search_images(project, "example_image_1")
    assert len(images) == 1

    sa.download_image(images[0], tmpdir, True)
    if project_type == 1:

        assert sa.get_image_preannotations(
            images[0]
        )["preannotation_json_filename"] is None
    else:
        try:
            sa.get_image_preannotations(images[0])
            assert False
        except sa.SABaseException as e:
            assert e.message == "Preannotation not available for pixel projects."
    assert sa.get_image_annotations(images[0]
                                   )["annotation_json_filename"] is None
    sa.download_image_annotations(images[0], tmpdir)
    assert len(list(Path(tmpdir).glob("*"))) == 1
    if project_type == 1:
        sa.download_image_preannotations(images[0], tmpdir)
        assert len(list(Path(tmpdir).glob("*"))) == 1
    else:
        try:
            sa.download_image_preannotations(images[0], tmpdir)
            assert False
        except sa.SABaseException as e:
            assert e.message == "Preannotation not available for pixel projects."

    assert (Path(tmpdir) / images[0]["name"]).is_file()

    sa.upload_annotations_from_file_to_image(
        images[0],
        sa.image_path_to_annotation_paths(
            from_folder / images[0]["name"], project_type
        )[0], None if project_type == 1 else sa.image_path_to_annotation_paths(
            from_folder / images[0]["name"], project_type
        )[1], old_to_new_classes_conversion
    )
    assert sa.get_image_annotations(images[0]
                                   )["annotation_json_filename"] is not None

    sa.download_image_annotations(images[0], tmpdir)
    annotation = list(Path(tmpdir).glob("*.json"))
    assert len(annotation) == 1
    annotation = json.load(open(annotation[0]))

    sa.download_annotation_classes_json(project, tmpdir)
    downloaded_classes = json.load(open(tmpdir / "classes.json"))

    for a in annotation:
        found = False
        if a['classId'] == -1:
            continue
        for c1 in downloaded_classes:
            if a["classId"] == c1["id"]:
                found = True
                break
        assert found

    input_classes = json.load(open(from_folder / "classes" / "classes.json"))
    assert len(downloaded_classes) == len(input_classes)
    for c1 in downloaded_classes:
        found = False
        for c2 in input_classes:
            if c1["name"] == c2["name"]:
                found = True
                break
        assert found

    sa.delete_project(project)


def test_large_project_images():
    team = sa.get_default_team()
    project = sa.search_projects(team, "test_ya14")[0]
    images = sa.search_images(project)
    assert len(images) == 38675
    image_info = sa.get_image_metadata(images[0])
    assert image_info["name"] == images[0]["name"]
