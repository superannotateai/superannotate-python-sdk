from pathlib import Path

import superannotate as sa

sa.init(Path.home() / ".superannotate" / "config.json")

TEMP_PROJECT_NAME = "test_recursive"


def test_nonrecursive_annotations_folder(tmpdir):
    tmpdir = Path(tmpdir)
    projects_found = sa.search_projects(TEMP_PROJECT_NAME)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(TEMP_PROJECT_NAME, "test", "Vector")

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

    sa.download_export(project, export, tmpdir)

    assert len(list(tmpdir.glob("*.json"))) == 1


def test_recursive_annotations_folder(tmpdir):
    tmpdir = Path(tmpdir)
    projects_found = sa.search_projects(TEMP_PROJECT_NAME)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(TEMP_PROJECT_NAME, "test", "Vector")

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

    sa.download_export(project, export, tmpdir)

    assert len(list(tmpdir.glob("*.json"))) == 2


def test_recursive_preannotations_folder(tmpdir):
    tmpdir = Path(tmpdir)
    projects_found = sa.search_projects(TEMP_PROJECT_NAME)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(TEMP_PROJECT_NAME, "test", "Vector")

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

    for image in sa.search_images(project):
        sa.download_image_preannotations(project, image, tmpdir)

    assert len(list(tmpdir.glob("*.json"))) == 2


def test_nonrecursive_preannotations_folder(tmpdir):
    tmpdir = Path(tmpdir)
    projects_found = sa.search_projects(TEMP_PROJECT_NAME)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(TEMP_PROJECT_NAME, "test", "Vector")

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

    for image in sa.search_images(project):
        sa.download_image_preannotations(project, image, tmpdir)

    assert len(list(tmpdir.glob("*.json"))) == 1


def test_annotations_recursive_s3_folder(tmpdir):
    tmpdir = Path(tmpdir)
    projects_found = sa.search_projects(TEMP_PROJECT_NAME)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(TEMP_PROJECT_NAME, "test", "Vector")

    sa.upload_images_from_folder_to_project(
        project,
        "sample_recursive_test",
        annotation_status="QualityCheck",
        from_s3_bucket="hovnatan-test",
        recursive_subfolders=True
    )

    assert len(sa.search_images(project)) == 2

    sa.create_annotation_classes_from_classes_json(
        project,
        "sample_recursive_test/classes/classes.json",
        from_s3_bucket="hovnatan-test"
    )

    sa.upload_annotations_from_folder_to_project(
        project,
        "sample_recursive_test",
        recursive_subfolders=True,
        from_s3_bucket="hovnatan-test"
    )

    export = sa.prepare_export(project)

    sa.download_export(project, export, tmpdir)

    assert len(list(tmpdir.glob("*.json"))) == 2


def test_annotations_nonrecursive_s3_folder(tmpdir):
    tmpdir = Path(tmpdir)
    projects_found = sa.search_projects(TEMP_PROJECT_NAME)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(TEMP_PROJECT_NAME, "test", "Vector")

    sa.upload_images_from_folder_to_project(
        project,
        "sample_recursive_test",
        annotation_status="QualityCheck",
        from_s3_bucket="hovnatan-test",
        recursive_subfolders=True
    )

    assert len(sa.search_images(project)) == 2

    sa.create_annotation_classes_from_classes_json(
        project,
        "sample_recursive_test/classes/classes.json",
        from_s3_bucket="hovnatan-test"
    )

    sa.upload_annotations_from_folder_to_project(
        project,
        "sample_recursive_test",
        recursive_subfolders=False,
        from_s3_bucket="hovnatan-test"
    )

    export = sa.prepare_export(project)

    sa.download_export(project, export, tmpdir)

    assert len(list(tmpdir.glob("*.json"))) == 1


def test_preannotations_recursive_s3_folder(tmpdir):
    tmpdir = Path(tmpdir)
    projects_found = sa.search_projects(TEMP_PROJECT_NAME)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(TEMP_PROJECT_NAME, "test", "Vector")

    sa.upload_images_from_folder_to_project(
        project,
        "sample_recursive_test",
        from_s3_bucket="hovnatan-test",
        recursive_subfolders=True
    )

    assert len(sa.search_images(project)) == 2

    sa.create_annotation_classes_from_classes_json(
        project,
        "sample_recursive_test/classes/classes.json",
        from_s3_bucket="hovnatan-test"
    )

    sa.upload_preannotations_from_folder_to_project(
        project,
        "sample_recursive_test",
        recursive_subfolders=True,
        from_s3_bucket="hovnatan-test"
    )

    for image in sa.search_images(project):
        sa.download_image_preannotations(project, image, tmpdir)

    assert len(list(tmpdir.glob("*.json"))) == 2


def test_preannotations_nonrecursive_s3_folder(tmpdir):
    tmpdir = Path(tmpdir)
    projects_found = sa.search_projects(TEMP_PROJECT_NAME)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(TEMP_PROJECT_NAME, "test", "Vector")

    sa.upload_images_from_folder_to_project(
        project,
        "sample_recursive_test",
        from_s3_bucket="hovnatan-test",
        recursive_subfolders=True
    )

    assert len(sa.search_images(project)) == 2

    sa.create_annotation_classes_from_classes_json(
        project,
        "sample_recursive_test/classes/classes.json",
        from_s3_bucket="hovnatan-test"
    )

    sa.upload_preannotations_from_folder_to_project(
        project,
        "sample_recursive_test",
        recursive_subfolders=False,
        from_s3_bucket="hovnatan-test"
    )

    for image in sa.search_images(project):
        sa.download_image_preannotations(project, image, tmpdir)


def test_images_nonrecursive_s3(tmpdir):
    tmpdir = Path(tmpdir)
    projects_found = sa.search_projects(TEMP_PROJECT_NAME)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(TEMP_PROJECT_NAME, "test", "Vector")

    sa.upload_images_from_folder_to_project(
        project,
        "sample_recursive_test",
        from_s3_bucket="hovnatan-test",
        recursive_subfolders=False
    )

    assert len(sa.search_images(project)) == 1


def test_images_nonrecursive(tmpdir):
    tmpdir = Path(tmpdir)
    projects_found = sa.search_projects(TEMP_PROJECT_NAME)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(TEMP_PROJECT_NAME, "test", "Vector")

    sa.upload_images_from_folder_to_project(
        project, "./tests/sample_recursive_test", recursive_subfolders=False
    )

    assert len(sa.search_images(project)) == 1
