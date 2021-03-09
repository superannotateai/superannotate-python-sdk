from pathlib import Path

import pytest
import superannotate as sa
from superannotate.exceptions import SABaseException

FROM_FOLDER = Path("./tests/sample_project_vector")


def test_basic_folders(tmpdir):
    PROJECT_NAME = "test folder simple"
    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(PROJECT_NAME, return_metadata=True)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(PROJECT_NAME, 'test', 'Vector')
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
    PROJECT_NAME = "test folder annotations"
    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(PROJECT_NAME, return_metadata=True)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(PROJECT_NAME, 'test', 'Vector')
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


def test_delete_folders(tmpdir):
    PROJECT_NAME = "test folder deletes"

    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(PROJECT_NAME, return_metadata=True)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(PROJECT_NAME, 'test', 'Vector')
    sa.create_folder(project, "folder1")
    sa.create_folder(project, "folder2")
    sa.create_folder(project, "folder3")

    assert len(sa.search_folders(project)) == 3

    sa.delete_folders(project, "folder1")
    assert len(sa.search_folders(project)) == 2
    sa.delete_folders(project, ["folder2", "folder3"])
    assert len(sa.search_folders(project)) == 0

    sa.create_folder(project, "folder5")
    sa.create_folder(project, "folder6")
    assert len(sa.search_folders(project)) == 2

    sa.delete_folders(project, ["folder2", "folder5"])
    assert len(sa.search_folders(project)) == 1
    assert sa.search_folders(project)[0] == "folder6"


def test_rename_folder(tmpdir):
    PROJECT_NAME = "test folder image count"
    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(PROJECT_NAME, return_metadata=True)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(PROJECT_NAME, 'test', 'Vector')
    sa.create_folder(project, "folder1")
    sa.create_folder(project, "folder2")
    sa.create_folder(project, "folder3")

    assert len(sa.search_folders(project)) == 3

    sa.rename_folder(project["name"] + "/folder1", "folder5")

    assert len(sa.search_folders(project)) == 3

    assert "folder5" in sa.search_folders(project)
    assert "folder1" not in sa.search_folders(project)

    print(sa.search_folders(project))


def test_project_folder_image_count(tmpdir):
    PROJECT_NAME = "test folder image count"
    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(PROJECT_NAME, return_metadata=True)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(PROJECT_NAME, 'test', 'Vector')
    project = project["name"]
    sa.upload_images_from_folder_to_project(
        project, FROM_FOLDER, annotation_status="InProgress"
    )
    num_images = sa.get_project_image_count(project)
    assert num_images == 4

    sa.create_folder(project, "folder1")

    sa.upload_images_from_folder_to_project(
        project + "/folder1", FROM_FOLDER, annotation_status="InProgress"
    )
    num_images = sa.get_project_image_count(project)
    assert num_images == 4

    num_images = sa.get_project_image_count(project + "/folder1")
    assert num_images == 4


def test_delete_images(tmpdir):
    PROJECT_NAME = "test delete folder images"
    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(PROJECT_NAME, return_metadata=True)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(PROJECT_NAME, 'test', 'Vector')
    sa.create_folder(project, "folder1")
    project = project["name"] + "/folder1"
    sa.upload_images_from_folder_to_project(
        project, FROM_FOLDER, annotation_status="InProgress"
    )
    num_images = sa.get_project_image_count(project)
    assert num_images == 4

    sa.delete_images(project, ["example_image_2.jpg", "example_image_3.jpg"])

    num_images = sa.get_project_image_count(project)
    assert num_images == 2