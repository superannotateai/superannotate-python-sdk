from pathlib import Path
import json

import pytest

import superannotate as sa

sa.init(Path.home() / ".superannotate" / "config.json")

PROJECT_NAME = "Example Project test annotation add"
PROJECT_NAME_NOINIT = "Example Project test annotation add no init"
PROJECT_DESCRIPTION = "test vector"
PATH_TO_SAMPLE_PROJECT = Path("./tests/sample_project_vector")


def test_add_bbox(tmpdir):
    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(PROJECT_NAME)
    for pr in projects_found:
        if pr["name"] == PROJECT_NAME:
            sa.delete_project(pr)

    project = sa.create_project(PROJECT_NAME, PROJECT_DESCRIPTION, "Vector")
    sa.upload_images_from_folder_to_project(
        project, PATH_TO_SAMPLE_PROJECT, annotation_status="InProgress"
    )
    sa.create_annotation_classes_from_classes_json(
        project, PATH_TO_SAMPLE_PROJECT / "classes" / "classes.json"
    )
    sa.create_annotation_class(project, "test_add", "#FF0000")
    sa.upload_annotations_from_folder_to_project(
        project, PATH_TO_SAMPLE_PROJECT
    )

    images = sa.search_images(project, "example_image_1")

    annotations = sa.get_image_annotations(images[0])["annotation_json"]

    sa.add_annotation_bbox_to_image(images[0], [10, 10, 500, 100], "test_add")
    annotations_new = sa.get_image_annotations(images[0])["annotation_json"]
    json.dump(annotations_new, open(tmpdir / "new_anns.json", "w"))

    assert len(annotations_new) == len(annotations) + 1

    export = sa.prepare_export(project, include_fuse=True)
    sa.download_export(export, tmpdir)

    annotations_new_export = json.load(
        open(tmpdir / f"{images[0]['name']}___objects.json")
    )
    assert len(annotations_new_export) == len(annotations) + 1

    annotations = sa.get_image_annotations(images[0])["annotation_json"]

    sa.add_annotation_polygon_to_image(
        images[0], [100, 100, 500, 500, 200, 300], "test_add"
    )
    annotations_new = sa.get_image_annotations(images[0])["annotation_json"]
    json.dump(annotations_new, open(tmpdir / "new_anns.json", "w"))

    assert len(annotations_new) == len(annotations) + 1

    export = sa.prepare_export(project, include_fuse=True)
    sa.download_export(export, tmpdir)

    annotations_new_export = json.load(
        open(tmpdir / f"{images[0]['name']}___objects.json")
    )
    assert len(annotations_new_export) == len(annotations) + 1

    annotations = sa.get_image_annotations(images[0])["annotation_json"]

    sa.add_annotation_polyline_to_image(
        images[0], [110, 110, 510, 510, 600, 510], "test_add"
    )
    annotations_new = sa.get_image_annotations(images[0])["annotation_json"]
    json.dump(annotations_new, open(tmpdir / "new_anns.json", "w"))

    assert len(annotations_new) == len(annotations) + 1

    export = sa.prepare_export(project, include_fuse=True)
    sa.download_export(export, tmpdir)

    annotations_new_export = json.load(
        open(tmpdir / f"{images[0]['name']}___objects.json")
    )
    assert len(annotations_new_export) == len(annotations) + 1

    annotations = sa.get_image_annotations(images[0])["annotation_json"]
    sa.add_annotation_point_to_image(images[0], [250, 250], "test_add")
    annotations_new = sa.get_image_annotations(images[0])["annotation_json"]
    json.dump(annotations_new, open(tmpdir / "new_anns.json", "w"))

    assert len(annotations_new) == len(annotations) + 1

    export = sa.prepare_export(project, include_fuse=True)
    sa.download_export(export, tmpdir)

    annotations_new_export = json.load(
        open(tmpdir / f"{images[0]['name']}___objects.json")
    )
    assert len(annotations_new_export) == len(annotations) + 1

    annotations = sa.get_image_annotations(images[0])["annotation_json"]
    sa.add_annotation_ellipse_to_image(
        images[0], [405, 405, 20, 70, 15], "test_add"
    )
    annotations_new = sa.get_image_annotations(images[0])["annotation_json"]
    json.dump(annotations_new, open(tmpdir / "new_anns.json", "w"))

    assert len(annotations_new) == len(annotations) + 1

    export = sa.prepare_export(project, include_fuse=True)
    sa.download_export(export, tmpdir)

    annotations_new_export = json.load(
        open(tmpdir / f"{images[0]['name']}___objects.json")
    )
    assert len(annotations_new_export) == len(annotations) + 1

    annotations = sa.get_image_annotations(images[0])["annotation_json"]
    sa.add_annotation_template_to_image(
        images[0], [600, 30, 630, 30, 615, 60], [1, 3, 2, 3], "test_add"
    )
    annotations_new = sa.get_image_annotations(images[0])["annotation_json"]
    json.dump(annotations_new, open(tmpdir / "new_anns.json", "w"))

    assert len(annotations_new) == len(annotations) + 1

    export = sa.prepare_export(project, include_fuse=True)
    sa.download_export(export, tmpdir)

    annotations_new_export = json.load(
        open(tmpdir / f"{images[0]['name']}___objects.json")
    )
    assert len(annotations_new_export) == len(annotations) + 1

    annotations = sa.get_image_annotations(images[0])["annotation_json"]
    sa.add_annotation_cuboid_to_image(
        images[0], [800, 500, 900, 600, 850, 450, 950, 700], "test_add"
    )
    annotations_new = sa.get_image_annotations(images[0])["annotation_json"]
    json.dump(annotations_new, open(tmpdir / "new_anns.json", "w"))

    assert len(annotations_new) == len(annotations) + 1

    export = sa.prepare_export(project, include_fuse=True)
    sa.download_export(export, tmpdir)

    annotations_new_export = json.load(
        open(tmpdir / f"{images[0]['name']}___objects.json")
    )
    assert len(annotations_new_export) == len(annotations) + 1


def test_add_bbox_noinit(tmpdir):
    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(PROJECT_NAME_NOINIT)
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

    sa.add_annotation_bbox_to_image(images[0], [10, 10, 500, 100], "test_add")
    annotations_new = sa.get_image_annotations(images[0])["annotation_json"]

    assert len(annotations_new) == 1
    export = sa.prepare_export(project, include_fuse=True)
    sa.download_export(export, tmpdir)
    assert len(list(Path(tmpdir).rglob("*.*"))) == 4
    annotations_new_export = json.load(
        open(tmpdir / f"{images[0]['name']}___objects.json")
    )
    assert len(annotations_new_export) == 1

    sa.add_annotation_polygon_to_image(
        images[0], [100, 100, 500, 500, 200, 300], "test_add"
    )
    annotations_new = sa.get_image_annotations(images[0])["annotation_json"]

    assert len(annotations_new) == 2
    export = sa.prepare_export(project, include_fuse=True)
    sa.download_export(export, tmpdir)
    assert len(list(Path(tmpdir).rglob("*.*"))) == 4
    annotations_new_export = json.load(
        open(tmpdir / f"{images[0]['name']}___objects.json")
    )
    assert len(annotations_new_export) == 2
