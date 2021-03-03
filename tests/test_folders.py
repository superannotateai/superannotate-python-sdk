from pathlib import Path

import pytest
import superannotate as sa
from superannotate.exceptions import SABaseException

PROJECT_NAME1 = "test folder simple"
PROJECT_NAME2 = "test folder annotations"

FROM_FOLDER = Path("./tests/sample_project_vector")


def test_basic_folders(tmpdir):
    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(PROJECT_NAME1, return_metadata=True)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(PROJECT_NAME1, 'test', 'Vector')
    project = project["name"]
    sa.upload_images_from_folder_to_project(
        project, FROM_FOLDER, annotation_status="InProgress"
    )
    images = sa.search_images(project, "example_image_1")
    assert len(images) == 1

    folders = sa.search_folders(project)
    assert len(folders) == 0

    folder_metadata = sa.create_folder(project, "folder1")
    assert folder_metadata["name"] == "folder1"

    folders = sa.search_folders(project, return_metadata=True)
    assert len(folders) == 1

    assert folders[0]["name"] == "folder1"

    folders = sa.search_folders(project)
    assert len(folders) == 1

    assert folders[0] == "folder1"

    images = sa.search_images(project + "/folder1", "example_image_1")
    assert len(images) == 0

    folder = sa.get_folder_metadata(project, "folder1")
    assert isinstance(folder, dict)
    assert folder["name"] == "folder1"

    with pytest.raises(SABaseException) as e:
        folder = sa.get_folder_metadata(project, "folder2")
    assert 'Folder not found' in str(e)

    sa.upload_images_from_folder_to_project(
        project + "/folder1", FROM_FOLDER, annotation_status="InProgress"
    )
    images = sa.search_images(project + "/folder1", "example_image_1")
    assert len(images) == 1

    sa.upload_images_from_folder_to_project(
        project + "/folder1", FROM_FOLDER, annotation_status="InProgress"
    )
    images = sa.search_images(project + "/folder1")
    assert len(images) == 4

    with pytest.raises(SABaseException) as e:
        sa.upload_images_from_folder_to_project(
            project + "/folder2", FROM_FOLDER, annotation_status="InProgress"
        )
    assert 'Folder not found' in str(e)

    folder_metadata = sa.create_folder(project, "folder2")
    assert folder_metadata["name"] == "folder2"

    folders = sa.search_folders(project)
    assert len(folders) == 2

    folders = sa.search_folders(project, folder_name="folder")
    assert len(folders) == 2

    folders = sa.search_folders(project, folder_name="folder2")
    assert len(folders) == 1
    assert folders[0] == "folder2"

    folders = sa.search_folders(project, folder_name="folder1")
    assert len(folders) == 1
    assert folders[0] == "folder1"

    folders = sa.search_folders(project, folder_name="old")
    assert len(folders) == 2


def test_folder_annotations(tmpdir):
    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(PROJECT_NAME2, return_metadata=True)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(PROJECT_NAME2, 'test', 'Vector')
    project = project["name"]
    sa.upload_images_from_folder_to_project(
        project, FROM_FOLDER, annotation_status="InProgress"
    )
    sa.create_annotation_classes_from_classes_json(
        project, FROM_FOLDER / "classes" / "classes.json"
    )
    folder_metadata = sa.create_folder(project, "folder1")
    assert folder_metadata["name"] == "folder1"

    folders = sa.search_folders(project, return_metadata=True)
    assert len(folders) == 1

    sa.upload_images_from_folder_to_project(
        project + "/" + folders[0]["name"],
        FROM_FOLDER,
        annotation_status="InProgress"
    )
    sa.upload_annotations_from_folder_to_project(
        project + "/" + folders[0]["name"], FROM_FOLDER
    )
    annot = sa.get_image_annotations(project, "example_image_1.jpg")
    assert len(annot["annotation_json"]["instances"]) == 0

    annot = sa.get_image_annotations(
        project + "/folder1", "example_image_1.jpg"
    )
    assert len(annot["annotation_json"]["instances"]) > 0