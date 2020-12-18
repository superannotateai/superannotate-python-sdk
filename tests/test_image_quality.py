from pathlib import Path
import filecmp

import superannotate as sa

PROJECT_NAME1 = "test image qual setting1"
PROJECT_NAME2 = "test image qual setting2"


def test_image_quality_setting1(tmpdir):
    tmpdir = Path(tmpdir)

    projects = sa.search_projects(PROJECT_NAME1, return_metadata=True)
    for project in projects:
        sa.delete_project(project)

    project = sa.create_project(PROJECT_NAME1, "test", "Vector")

    sa.upload_images_from_folder_to_project(
        project, "./tests/sample_project_vector"
    )

    sa.download_image(project, "example_image_1.jpg", tmpdir, variant="lores")

    assert not filecmp.cmp(
        tmpdir / "example_image_1.jpg___lores.jpg",
        "./tests/sample_project_vector/example_image_1.jpg",
        shallow=False
    )


def test_image_quality_setting2(tmpdir):
    tmpdir = Path(tmpdir)

    projects = sa.search_projects(PROJECT_NAME2, return_metadata=True)
    for project in projects:
        sa.delete_project(project)

    project = sa.create_project(PROJECT_NAME2, "test", "Vector")

    sa.set_project_default_image_quality_in_editor(project, "original")

    sa.upload_images_from_folder_to_project(
        project, "./tests/sample_project_vector"
    )

    sa.download_image(project, "example_image_1.jpg", tmpdir, variant="lores")

    assert filecmp.cmp(
        tmpdir / "example_image_1.jpg___lores.jpg",
        "./tests/sample_project_vector/example_image_1.jpg",
        shallow=False
    )
