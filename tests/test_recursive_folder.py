import json
from pathlib import Path
import time

import superannotate as sa
from .test_assign_images import safe_create_project


TEMP_PROJECT_NAME = "test_recursive"


def test_nonrecursive_annotations_folder(tmpdir):
    tmpdir = Path(tmpdir)

    project = safe_create_project(TEMP_PROJECT_NAME + "0", "test", "Vector")
    sa.upload_images_from_folder_to_project(
        project,
        "./tests/sample_recursive_test",
        annotation_status="QualityCheck",
        recursive_subfolders=True
    )

    assert len(sa.search_images(project)) == 2

    sa.create_annotation_classes_from_classes_json(
        project, "./tests/sample_recursive_test/classes/classes.json"
    )

    sa.upload_annotations_from_folder_to_project(
        project, "./tests/sample_recursive_test", recursive_subfolders=False
    )

    export = sa.prepare_export(project)

    time.sleep(2)
    sa.download_export(project, export, tmpdir)

    non_empty_annotations = 0
    json_files = tmpdir.glob("*.json")
    for json_file in json_files:
        json_ann = json.load(open(json_file))
        if "instances" in json_ann and len(json_ann["instances"]) > 0:
            non_empty_annotations += 1

    assert non_empty_annotations == 1


def test_recursive_annotations_folder(tmpdir):
    tmpdir = Path(tmpdir)

    project = safe_create_project(TEMP_PROJECT_NAME + "1", "test", "Vector")
    sa.upload_images_from_folder_to_project(
        project,
        "./tests/sample_recursive_test",
        annotation_status="QualityCheck",
        recursive_subfolders=True
    )

    assert len(sa.search_images(project)) == 2

    sa.create_annotation_classes_from_classes_json(
        project, "./tests/sample_recursive_test/classes/classes.json"
    )

    sa.upload_annotations_from_folder_to_project(
        project, "./tests/sample_recursive_test", recursive_subfolders=True
    )

    export = sa.prepare_export(project)

    time.sleep(1)
    sa.download_export(project, export, tmpdir)

    assert len(list(tmpdir.glob("*.json"))) == 2


def test_recursive_preannotations_folder(tmpdir):
    tmpdir = Path(tmpdir)

    project = safe_create_project(TEMP_PROJECT_NAME + "2", "test", "Vector")

    sa.upload_images_from_folder_to_project(
        project,
        "./tests/sample_recursive_test",
        annotation_status="QualityCheck",
        recursive_subfolders=True
    )

    assert len(sa.search_images(project)) == 2

    sa.create_annotation_classes_from_classes_json(
        project, "./tests/sample_recursive_test/classes/classes.json"
    )

    sa.upload_preannotations_from_folder_to_project(
        project, "./tests/sample_recursive_test", recursive_subfolders=True
    )

    time.sleep(2)

    for image in sa.search_images(project):
        sa.download_image_preannotations(project, image, tmpdir)

    assert len(list(tmpdir.glob("*.json"))) == 2


def test_nonrecursive_preannotations_folder(tmpdir):
    tmpdir = Path(tmpdir)

    project = safe_create_project(TEMP_PROJECT_NAME + "3", "test", "Vector")

    sa.upload_images_from_folder_to_project(
        project,
        "./tests/sample_recursive_test",
        annotation_status="QualityCheck",
        recursive_subfolders=True
    )

    assert len(sa.search_images(project)) == 2

    sa.create_annotation_classes_from_classes_json(
        project, "./tests/sample_recursive_test/classes/classes.json"
    )

    sa.upload_preannotations_from_folder_to_project(
        project, "./tests/sample_recursive_test", recursive_subfolders=False
    )

    time.sleep(2)
    for image in sa.search_images(project):
        sa.download_image_preannotations(project, image, tmpdir)

    assert len(list(tmpdir.glob("*.json"))) == 1


def test_annotations_recursive_s3_folder(tmpdir):
    tmpdir = Path(tmpdir)

    project = safe_create_project(TEMP_PROJECT_NAME + "4", "test", "Vector")

    sa.upload_images_from_folder_to_project(
        project,
        "sample_recursive_test",
        annotation_status="QualityCheck",
        from_s3_bucket="superannotate-python-sdk-test",
        recursive_subfolders=True
    )

    assert len(sa.search_images(project)) == 2

    sa.create_annotation_classes_from_classes_json(
        project,
        "sample_recursive_test/classes/classes.json",
        from_s3_bucket="superannotate-python-sdk-test"
    )

    sa.upload_annotations_from_folder_to_project(
        project,
        "sample_recursive_test",
        recursive_subfolders=True,
        from_s3_bucket="superannotate-python-sdk-test"
    )
    time.sleep(2)

    export = sa.prepare_export(project)

    time.sleep(2)
    sa.download_export(project, export, tmpdir)

    assert len(list(tmpdir.glob("*.json"))) == 2


def test_annotations_nonrecursive_s3_folder(tmpdir):
    tmpdir = Path(tmpdir)

    project = safe_create_project(TEMP_PROJECT_NAME + "5", "test", "Vector")

    sa.upload_images_from_folder_to_project(
        project,
        "sample_recursive_test",
        annotation_status="QualityCheck",
        from_s3_bucket="superannotate-python-sdk-test",
        recursive_subfolders=True
    )

    assert len(sa.search_images(project)) == 2

    sa.create_annotation_classes_from_classes_json(
        project,
        "sample_recursive_test/classes/classes.json",
        from_s3_bucket="superannotate-python-sdk-test"
    )

    sa.upload_annotations_from_folder_to_project(
        project,
        "sample_recursive_test",
        recursive_subfolders=False,
        from_s3_bucket="superannotate-python-sdk-test"
    )

    export = sa.prepare_export(project)

    time.sleep(1)
    sa.download_export(project, export, tmpdir)
    non_empty_annotations = 0
    json_files = tmpdir.glob("*.json")
    for json_file in json_files:
        json_ann = json.load(open(json_file))
        if "instances" in json_ann and len(json_ann["instances"]) > 0:
            non_empty_annotations += 1

    assert non_empty_annotations == 1


def test_preannotations_recursive_s3_folder(tmpdir):
    tmpdir = Path(tmpdir)


    project = safe_create_project(TEMP_PROJECT_NAME + "6", "test", "Vector")


    sa.upload_images_from_folder_to_project(
        project,
        "sample_recursive_test",
        from_s3_bucket="superannotate-python-sdk-test",
        recursive_subfolders=True
    )
    time.sleep(2)

    assert len(sa.search_images(project)) == 2

    sa.create_annotation_classes_from_classes_json(
        project,
        "sample_recursive_test/classes/classes.json",
        from_s3_bucket="superannotate-python-sdk-test"
    )

    sa.upload_preannotations_from_folder_to_project(
        project,
        "sample_recursive_test",
        recursive_subfolders=True,
        from_s3_bucket="superannotate-python-sdk-test"
    )
    time.sleep(2)

    for image in sa.search_images(project):
        sa.download_image_preannotations(project, image, tmpdir)

    assert len(list(tmpdir.glob("*.json"))) == 2


def test_preannotations_nonrecursive_s3_folder(tmpdir):
    tmpdir = Path(tmpdir)

    project = safe_create_project(TEMP_PROJECT_NAME + "7", "test", "Vector")

    sa.upload_images_from_folder_to_project(
        project,
        "sample_recursive_test",
        from_s3_bucket="superannotate-python-sdk-test",
        recursive_subfolders=True
    )
    time.sleep(2)

    assert len(sa.search_images(project)) == 2

    sa.create_annotation_classes_from_classes_json(
        project,
        "sample_recursive_test/classes/classes.json",
        from_s3_bucket="superannotate-python-sdk-test"
    )

    sa.upload_preannotations_from_folder_to_project(
        project,
        "sample_recursive_test",
        recursive_subfolders=False,
        from_s3_bucket="superannotate-python-sdk-test"
    )
    time.sleep(2)

    for image in sa.search_images(project):
        sa.download_image_preannotations(project, image, tmpdir)


def test_images_nonrecursive_s3(tmpdir):

    project = safe_create_project(TEMP_PROJECT_NAME + "8", "test", "Vector")

    sa.upload_images_from_folder_to_project(
        project,
        "sample_recursive_test",
        from_s3_bucket="superannotate-python-sdk-test",
        recursive_subfolders=False
    )
    time.sleep(2)

    assert len(sa.search_images(project)) == 1


def test_images_nonrecursive(tmpdir):
    project = safe_create_project(TEMP_PROJECT_NAME + "9", "test", "Vector")

    sa.upload_images_from_folder_to_project(
        project, "./tests/sample_recursive_test", recursive_subfolders=False
    )
    time.sleep(2)
    assert len(sa.search_images(project)) == 1
