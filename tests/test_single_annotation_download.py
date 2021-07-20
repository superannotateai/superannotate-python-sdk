import filecmp
import json
import time
from pathlib import Path

import pytest

import superannotate as sa

from .common import upload_project


@pytest.mark.parametrize(
    "project_type,name,description,from_folder", [
        (
            "Vector",
            "Example Project test vector single annotation upload download",
            "test vector", Path("./tests/sample_project_vector")
        ),
        (
            "Pixel",
            "Example Project test pixel single annotation upload download",
            "test pixel", Path("./tests/sample_project_pixel")
        )
    ]
)
def test_annotation_download_upload(
    project_type, name, description, from_folder, tmpdir
):
    # projects = sa.search_projects(name, return_metadata=True)
    # for project in projects:
    #     sa.delete_project(project)

    # project = sa.create_project(name, description, project_type)

    # sa.upload_images_from_folder_to_project(
    #     project, from_folder, annotation_status="NotStarted"
    # )
    # sa.create_annotation_classes_from_classes_json(
    #     project, from_folder / "classes" / "classes.json"
    # )
    # sa.upload_annotations_from_folder_to_project(project, from_folder)

    project = upload_project(from_folder, name, description, project_type)

    time.sleep(2)
    image = sa.search_images(project)[0]
    paths = sa.download_image_annotations(project, image, tmpdir)

    input_annotation_paths_after = sa.image_path_to_annotation_paths(
        tmpdir / image, project_type
    )

    assert paths[0] == str(input_annotation_paths_after[0])
    if project_type == "Pixel":
        assert paths[1] == str(input_annotation_paths_after[1])
    else:
        assert len(paths) == 1

    anns_json_in_folder = list(Path(tmpdir).glob("*.json"))
    anns_mask_in_folder = list(Path(tmpdir).glob("*.png"))
    assert len(anns_json_in_folder) == 1
    assert len(anns_mask_in_folder) == (1 if project_type == "Pixel" else 0)

    input_annotation_paths = sa.image_path_to_annotation_paths(
        from_folder / image, project_type
    )

    json1 = json.load(open(input_annotation_paths[0]))
    json2 = json.load(open(anns_json_in_folder[0]))
    for i in json1["instances"]:
        i.pop("classId", None)
        for j in i["attributes"]:
            j.pop("groupId", None)
            j.pop("id", None)
    for i in json2["instances"]:
        i.pop("classId", None)
        for j in i["attributes"]:
            j.pop("groupId", None)
            j.pop("id", None)
    assert json1 == json2
    if project_type == "Pixel":
        assert filecmp.cmp(
            input_annotation_paths[1], anns_mask_in_folder[0], shallow=False
        )
