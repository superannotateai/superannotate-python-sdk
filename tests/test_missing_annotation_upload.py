from pathlib import Path

import superannotate as sa

def test_missing_annotation_upload(tmpdir):
    name = "Example Project test vector missing annotation upload"
    project_type = "Vector"
    description = "test vector"
    from_folder = Path("./tests/sample_project_vector_for_checks")
    projects = sa.search_projects(name, return_metadata=True)
    for project in projects:
        sa.delete_project(project)

    project = sa.create_project(name, description, project_type)

    sa.upload_images_from_folder_to_project(
        project, from_folder, annotation_status="NotStarted"
    )
    sa.create_annotation_classes_from_classes_json(
        project, from_folder / "classes" / "classes.json"
    )
    uploaded, couldnt_upload, missing_images = sa.upload_annotations_from_folder_to_project(
        project, from_folder
    )
    print(uploaded, couldnt_upload, missing_images)
    assert len(uploaded) == 2
    assert len(couldnt_upload) == 1
    assert len(missing_images) == 1

    assert uploaded[
        0
    ] == "tests/sample_project_vector_for_checks/example_image_1.jpg___objects.json"
    assert uploaded[
        1
    ] == "tests/sample_project_vector_for_checks/example_image_2.jpg___objects.json"
    assert couldnt_upload[
        0
    ] == "tests/sample_project_vector_for_checks/example_image_4.jpg___objects.json"
    assert missing_images[
        0
    ] == "tests/sample_project_vector_for_checks/example_image_5.jpg___objects.json"


def test_missing_preannotation_upload(tmpdir):
    name = "Example Project test vector missing preannotation upload"
    project_type = "Vector"
    description = "test vector"
    from_folder = Path("./tests/sample_project_vector_for_checks")


    projects = sa.search_projects(name, return_metadata=True)
    for project in projects:
        sa.delete_project(project)

    project = sa.create_project(name, description, project_type)

    sa.upload_images_from_folder_to_project(
        project, from_folder, annotation_status="NotStarted"
    )
    sa.create_annotation_classes_from_classes_json(
        project, from_folder / "classes" / "classes.json"
    )
    uploaded, couldnt_upload = sa.upload_preannotations_from_folder_to_project(
        project, from_folder
    )
    print(uploaded, couldnt_upload)
    assert len(uploaded) == 3
    assert len(couldnt_upload) == 1

    assert uploaded[
        0
    ] == "tests/sample_project_vector_for_checks/example_image_1.jpg___objects.json"
    assert uploaded[
        1
    ] == "tests/sample_project_vector_for_checks/example_image_2.jpg___objects.json"
    assert uploaded[
        2
    ] == "tests/sample_project_vector_for_checks/example_image_5.jpg___objects.json"
    assert couldnt_upload[
        0
    ] == "tests/sample_project_vector_for_checks/example_image_4.jpg___objects.json"