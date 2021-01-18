from pathlib import Path
import json

import pytest

import superannotate as sa

sa.init(Path.home() / ".superannotate" / "config.json")


@pytest.mark.parametrize(
    "project_type,name,description,from_folder", [
        (
            "Vector", "Example Project test vector basic images", "test vector",
            Path("./tests/sample_project_vector")
        ),
        (
            "Pixel", "Example Project test pixel basic images", "test pixel",
            Path("./tests/sample_project_pixel")
        ),
    ]
)
def test_basic_images(project_type, name, description, from_folder, tmpdir):
    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(name, return_metadata=True)
    for pr in projects_found:
        sa.delete_project(pr)

    projects_found = sa.search_projects(name, return_metadata=True)
    project = sa.create_project(name, description, project_type)
    sa.upload_images_from_folder_to_project(
        project, from_folder, annotation_status="InProgress"
    )
    sa.create_annotation_classes_from_classes_json(
        project, from_folder / "classes" / "classes.json"
    )
    images = sa.search_images(project, "example_image_1")
    assert len(images) == 1

    image_name = images[0]
    sa.download_image(project, image_name, tmpdir, True)
    assert sa.get_image_preannotations(project, image_name
                                      )["preannotation_json_filename"] is None
    assert len(
        sa.get_image_annotations(project,
                                 image_name)["annotation_json"]["instances"]
    ) == 0
    sa.download_image_annotations(project, image_name, tmpdir)
    assert len(list(Path(tmpdir).glob("*"))) == 2
    sa.download_image_preannotations(project, image_name, tmpdir)
    assert len(list(Path(tmpdir).glob("*"))) == 2

    assert (Path(tmpdir) / image_name).is_file()

    sa.upload_image_annotations(
        project, image_name,
        sa.image_path_to_annotation_paths(
            from_folder / image_name, project_type
        )[0], None if project_type == "Vector" else sa.
        image_path_to_annotation_paths(from_folder /
                                       image_name, project_type)[1]
    )
    assert sa.get_image_annotations(project, image_name
                                   )["annotation_json_filename"] is not None

    sa.download_image_annotations(project, image_name, tmpdir)
    annotation = list(Path(tmpdir).glob("*.json"))
    assert len(annotation) == 1
    annotation = json.load(open(annotation[0]))

    sa.download_annotation_classes_json(project, tmpdir)
    downloaded_classes = json.load(open(tmpdir / "classes.json"))

    for a in annotation:
        if "className" not in a:
            continue
        for c1 in downloaded_classes:
            if a["className"] == c1["name"] or a[
                "className"
            ] == "Personal vehicle1":  # "Personal vehicle1" is not existing class in annotations
                break
        else:
            assert False

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
