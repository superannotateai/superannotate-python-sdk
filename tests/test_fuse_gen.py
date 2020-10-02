from pathlib import Path

import numpy as np
import pytest
from PIL import Image

import superannotate as sa

PROJECT_NAME = "test fuse image create"


def test_fuse_image_create(tmpdir):
    tmpdir = Path(tmpdir)

    projects = sa.search_projects(PROJECT_NAME, return_metadata=True)
    for project in projects:
        sa.delete_project(project)

    project = sa.create_project(PROJECT_NAME, "test", "Vector")

    sa.upload_image_to_project(
        project,
        "./tests/sample_project_vector/example_image_1.jpg",
        annotation_status="QualityCheck"
    )

    sa.create_annotation_classes_from_classes_json(
        project, "./tests/sample_project_vector/classes/classes.json"
    )

    sa.add_annotation_bbox_to_image(
        project, "example_image_1.jpg", [10, 10, 20, 20], "Human"
    )
    # sa.add_annotation_polygon_to_image(
    #     project, "example_image_1.jpg", [30, 30, 50, 50, 40, 50],
    #     "Personal vehicle"
    # )

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
    im1 = Image.open(tmpdir / "export" / "example_image_1.jpg___fuse.png")
    im1_array = np.array(im1)

    im2 = Image.open(paths[2])
    im2_array = np.array(im2)

    print(im1_array.shape, im2_array.shape)
    print(im1_array.dtype, im2_array.dtype)

    assert np.array_equal(im1_array, im2_array)
