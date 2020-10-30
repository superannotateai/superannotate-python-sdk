from pathlib import Path
import json
import time

import pytest

import superannotate as sa

sa.init(Path.home() / ".superannotate" / "config.json")

PROJECT_NAME = "Example Project test annotation add"
PROJECT_NAME_NOINIT = "Example Project test annotation add no init"
PROJECT_DESCRIPTION = "test vector"
PATH_TO_SAMPLE_PROJECT = Path("./tests/sample_project_vector")


def test_add_bbox(tmpdir):
    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(PROJECT_NAME, return_metadata=True)
    for pr in projects_found:
        if pr["name"] == PROJECT_NAME:
            sa.delete_project(pr)

    project = sa.create_project(PROJECT_NAME, PROJECT_DESCRIPTION, "Vector")
    sa.upload_images_from_folder_to_project(
        PROJECT_NAME, PATH_TO_SAMPLE_PROJECT, annotation_status="InProgress"
    )
    sa.create_annotation_classes_from_classes_json(
        project, PATH_TO_SAMPLE_PROJECT / "classes" / "classes.json"
    )
    sa.create_annotation_class(
        project, "test_add", "#FF0000", [
            {
                "name": "height",
                "attributes": [{
                    "name": "tall"
                }, {
                    "name": "short"
                }]
            }
        ]
    )
    sa.upload_annotations_from_folder_to_project(
        project, PATH_TO_SAMPLE_PROJECT
    )

    images = sa.search_images(project, "example_image_1")

    image_name = images[0]
    annotations = sa.get_image_annotations(project,
                                           image_name)["annotation_json"]

    sa.add_annotation_bbox_to_image(
        project, image_name, [10, 10, 500, 100], "test_add"
    )
    sa.add_annotation_polyline_to_image(
        project, image_name, [110, 110, 510, 510, 600, 510], "test_add"
    )
    sa.add_annotation_polygon_to_image(
        project, image_name, [100, 100, 500, 500, 200, 300], "test_add",
        [{
            "name": "tall",
            "groupName": "height"
        }]
    )
    sa.add_annotation_point_to_image(
        project, image_name, [250, 250], "test_add"
    )
    sa.add_annotation_ellipse_to_image(
        project, image_name, [405, 405, 20, 70, 15], "test_add"
    )
    sa.add_annotation_template_to_image(
        project, image_name, [600, 30, 630, 30, 615, 60], [1, 3, 2, 3],
        "test_add"
    )
    sa.add_annotation_cuboid_to_image(
        project, image_name, [800, 500, 900, 600, 850, 450, 950, 700],
        "test_add"
    )
    sa.add_annotation_comment_to_image(
        project, image_name, "hey", [100, 100], "hovnatan@superannotate.com",
        True
    )
    annotations_new = sa.get_image_annotations(project,
                                               image_name)["annotation_json"]
    json.dump(annotations_new, open(tmpdir / "new_anns.json", "w"))

    assert len(annotations_new) == len(annotations) + 8

    export = sa.prepare_export(project, include_fuse=True)
    sa.download_export(project, export, tmpdir)

    df = sa.aggregate_annotations_as_df(tmpdir)

    num = len(df[df["imageName"] == image_name]["instanceId"].dropna().unique())

    assert num == len(annotations) - 3 + 7


def test_add_bbox_noinit(tmpdir):
    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(
        PROJECT_NAME_NOINIT, return_metadata=True
    )
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(
        PROJECT_NAME_NOINIT, PROJECT_DESCRIPTION, "Vector"
    )
    sa.upload_images_from_folder_to_project(
        project, PATH_TO_SAMPLE_PROJECT, annotation_status="InProgress"
    )
    sa.create_annotation_classes_from_classes_json(
        project, PATH_TO_SAMPLE_PROJECT / "classes" / "classes.json"
    )
    sa.create_annotation_class(project, "test_add", "#FF0000")
    images = sa.search_images(project, "example_image_1")

    image_name = images[0]
    sa.add_annotation_bbox_to_image(
        project, image_name, [10, 10, 500, 100], "test_add"
    )
    sa.add_annotation_polygon_to_image(
        project, image_name, [100, 100, 500, 500, 200, 300], "test_add"
    )
    annotations_new = sa.get_image_annotations(project,
                                               image_name)["annotation_json"]

    assert len(annotations_new) == 2
    export = sa.prepare_export(project, include_fuse=True)
    sa.download_export(project, export, tmpdir)
    assert len(list(Path(tmpdir).rglob("*.*"))) == 4
