from pathlib import Path
from urllib.parse import urlparse

import pytest

import superannotate as sa
sa.init(Path.home() / ".superannotate" / "config.json")

TEST_PROJECT_PIXEL = "sample_project_pixel"
TEST_PROJECT_VECTOR = "sample_project_vector"


@pytest.fixture
def empty_test_project():
    projects_found = sa.search_projects("test_upload_41")
    for pr in projects_found:
        sa.delete_project(pr)


def test_upload_from_s3(empty_test_project, tmpdir):
    project = sa.create_project(
        "test_upload_41", "hk_test", project_type="Pixel"
    )

    f = urlparse(f"s3://hovnatan-test/{TEST_PROJECT_PIXEL}")
    sa.upload_images_from_folder_to_project(
        project,
        f.path[1:],
        annotation_status="NotStarted",
        from_s3_bucket=f.netloc
    )
    sa.create_annotation_classes_from_classes_json(
        project, f.path[1:] + '/classes/classes.json', from_s3_bucket=f.netloc
    )
    assert sa.get_project_image_count(project) == 3

    sa.upload_annotations_from_folder_to_project(
        project, TEST_PROJECT_PIXEL, from_s3_bucket=f.netloc
    )

    for image in sa.search_images(project):
        sa.download_image_annotations(project, image, tmpdir)

    assert len(list(Path(tmpdir).glob("*.*"))) == 6
    sa.delete_project(project)


def test_pixel_preannotation_upload_from_s3(empty_test_project, tmpdir):
    project = sa.create_project(
        "test_upload_41", "hk_test", project_type="Pixel"
    )

    f = urlparse(f"s3://hovnatan-test/{TEST_PROJECT_PIXEL}")
    sa.upload_images_from_folder_to_project(
        project,
        f.path[1:],
        annotation_status="NotStarted",
        from_s3_bucket=f.netloc
    )
    sa.create_annotation_classes_from_classes_json(
        project, f.path[1:] + '/classes/classes.json', from_s3_bucket=f.netloc
    )
    assert sa.get_project_image_count(project) == 3

    sa.upload_preannotations_from_folder_to_project(
        project, TEST_PROJECT_PIXEL, from_s3_bucket=f.netloc
    )

    for image in sa.search_images(project):
        sa.download_image_preannotations(project, image, tmpdir)

    assert len(list(Path(tmpdir).glob("*.*"))) == 6
    sa.delete_project(project)


def test_vector_preannotation_upload_from_s3(empty_test_project, tmpdir):
    project = sa.create_project(
        "test_upload_41", "hk_test", project_type="Vector"
    )

    f = urlparse(f"s3://hovnatan-test/{TEST_PROJECT_VECTOR}")
    sa.upload_images_from_folder_to_project(
        project,
        f.path[1:],
        annotation_status="NotStarted",
        from_s3_bucket=f.netloc
    )
    sa.create_annotation_classes_from_classes_json(
        project, f.path[1:] + '/classes/classes.json', from_s3_bucket=f.netloc
    )
    assert sa.get_project_image_count(project) == 4

    sa.upload_preannotations_from_folder_to_project(
        project, TEST_PROJECT_VECTOR, from_s3_bucket=f.netloc
    )

    for image in sa.search_images(project):
        sa.download_image_preannotations(project, image, tmpdir)

    assert len(list(Path(tmpdir).glob("*.*"))) == 4
    sa.delete_project(project)
