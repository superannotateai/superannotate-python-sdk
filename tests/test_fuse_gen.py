from pathlib import Path

import numpy as np
import pytest
from PIL import Image

import superannotate as sa

PROJECT_NAME_VECTOR = "test fuse image create vector"
PROJECT_NAME_PIXEL = "test fuse image create pixel"


def test_fuse_image_create_vector(tmpdir):
    tmpdir = Path(tmpdir)

    projects = sa.search_projects(PROJECT_NAME_VECTOR, return_metadata=True)
    for project in projects:
        sa.delete_project(project)

    project = sa.create_project(PROJECT_NAME_VECTOR, "test", "Vector")

    sa.upload_image_to_project(
        project,
        "./tests/sample_project_vector/example_image_1.jpg",
        annotation_status="QualityCheck"
    )

    sa.create_annotation_classes_from_classes_json(
        project, "./tests/sample_project_vector/classes/classes.json"
    )

    sa.add_annotation_bbox_to_image(
        project, "example_image_1.jpg", [20, 20, 40, 40], "Human"
    )
    sa.add_annotation_polygon_to_image(
        project, "example_image_1.jpg", [60, 60, 100, 100, 80, 100],
        "Personal vehicle"
    )
    sa.add_annotation_polyline_to_image(
        project, "example_image_1.jpg", [200, 200, 300, 200, 350, 300],
        "Personal vehicle"
    )
    sa.add_annotation_point_to_image(
        project, "example_image_1.jpg", [400, 400], "Personal vehicle"
    )
    sa.add_annotation_ellipse_to_image(
        project, "example_image_1.jpg", [600, 600, 50, 100, 20],
        "Personal vehicle"
    )
    sa.add_annotation_template_to_image(
        project, "example_image_1.jpg",
        [600, 300, 600, 350, 550, 250, 650, 250, 550, 400, 650, 400],
        [1, 2, 3, 1, 4, 1, 5, 2, 6, 2], "Human"
    )
    sa.add_annotation_cuboid_to_image(
        project, "example_image_1.jpg", [60, 300, 200, 350, 120, 325, 250, 500],
        "Human"
    )

    export = sa.prepare_export(project, include_fuse=True)
    (tmpdir / "export").mkdir()
    sa.download_export(project, export, (tmpdir / "export"))

    # sa.create_fuse_image(
    #     "./tests/sample_project_vector/example_image_1.jpg",
    #     "./tests/sample_project_vector/classes/classes.json", "Vector"
    # )

    paths = sa.download_image(
        project,
        "example_image_1.jpg",
        tmpdir,
        include_annotations=True,
        include_fuse=True,
        include_overlay=True
    )
    im1 = Image.open(tmpdir / "export" / "example_image_1.jpg___fuse.png")
    im1_array = np.array(im1)

    im2 = Image.open(paths[2][0])
    im2_array = np.array(im2)

    assert im1_array.shape == im2_array.shape
    assert im1_array.dtype == im2_array.dtype


def test_fuse_image_create_pixel(tmpdir):
    tmpdir = Path(tmpdir)

    projects = sa.search_projects(PROJECT_NAME_PIXEL, return_metadata=True)
    for project in projects:
        sa.delete_project(project)

    project = sa.create_project(PROJECT_NAME_PIXEL, "test", "Pixel")

    sa.upload_image_to_project(
        project,
        "./tests/sample_project_pixel/example_image_1.jpg",
        annotation_status="QualityCheck"
    )

    sa.create_annotation_classes_from_classes_json(
        project, "./tests/sample_project_pixel/classes/classes.json"
    )
    sa.upload_annotations_from_json_to_image(
        PROJECT_NAME_PIXEL, "example_image_1.jpg",
        "./tests/sample_project_pixel/example_image_1.jpg___pixel.json",
        "./tests/sample_project_pixel/example_image_1.jpg___save.png"
    )

    export = sa.prepare_export(project, include_fuse=True)
    (tmpdir / "export").mkdir()
    sa.download_export(project, export, (tmpdir / "export"))

    # sa.create_fuse_image(
    #     "./tests/sample_project_vector/example_image_1.jpg",
    #     "./tests/sample_project_vector/classes/classes.json", "Vector"
    # )

    paths = sa.download_image(
        project,
        "example_image_1.jpg",
        tmpdir,
        include_annotations=True,
        include_fuse=True
    )
    print(paths, paths[2])
    im1 = Image.open(tmpdir / "export" / "example_image_1.jpg___fuse.png")
    im1_array = np.array(im1)

    im2 = Image.open(paths[2][0])
    im2_array = np.array(im2)

    assert im1_array.shape == im2_array.shape
    assert im1_array.dtype == im2_array.dtype
    assert np.array_equal(im1_array, im2_array)
