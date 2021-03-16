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

    sa.delete_folders(project, ["folder1"])
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
    PROJECT_NAME = "test rename folder"
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

    sa.delete_images(project, None)
    num_images = sa.get_project_image_count(project)
    assert num_images == 0


def test_copy_images(tmpdir):
    PROJECT_NAME = "test copy folder images"
    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(PROJECT_NAME, return_metadata=True)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(PROJECT_NAME, 'test', 'Vector')
    sa.create_folder(project, "folder1")
    project = PROJECT_NAME + "/folder1"
    sa.upload_images_from_folder_to_project(
        project, FROM_FOLDER, annotation_status="InProgress"
    )
    num_images = sa.get_project_image_count(project)
    assert num_images == 4

    im1 = sa.get_image_metadata(project, "example_image_2.jpg")
    assert im1["annotation_status"] == "InProgress"

    sa.create_folder(PROJECT_NAME, "folder2")
    project2 = PROJECT_NAME + "/folder2"
    num_images = sa.get_project_image_count(project2)
    assert num_images == 0

    sa.copy_images(
        project,
        project2, ["example_image_2.jpg", "example_image_3.jpg"],
        include_annotations=False,
        copy_annotation_status=False,
        copy_pin=False
    )

    im1_copied = sa.get_image_metadata(project2, "example_image_2.jpg")
    assert im1_copied["annotation_status"] == "NotStarted"

    ann2 = sa.get_image_annotations(project2, "example_image_2.jpg")

    assert len(ann2["annotation_json"]["instances"]) == 0

    num_images = sa.get_project_image_count(project2)
    assert num_images == 2

    res = sa.copy_images(project, project2, None)

    num_images = sa.get_project_image_count(project2)
    assert num_images == 4

    assert res == 2


def test_move_images(tmpdir):
    PROJECT_NAME = "test move folder images1"
    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(PROJECT_NAME, return_metadata=True)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(PROJECT_NAME, 'test', 'Vector')
    sa.create_folder(project, "folder1")
    project = PROJECT_NAME + "/folder1"
    sa.upload_images_from_folder_to_project(
        project, FROM_FOLDER, annotation_status="InProgress"
    )
    num_images = sa.get_project_image_count(project)
    assert num_images == 4

    sa.create_folder(PROJECT_NAME, "folder2")
    project2 = PROJECT_NAME + "/folder2"
    num_images = sa.get_project_image_count(project2)
    assert num_images == 0

    sa.move_images(project, project2, ["example_image_2.jpg"])

    num_images = sa.get_project_image_count(project2)
    assert num_images == 1

    num_images = sa.get_project_image_count(project)
    assert num_images == 3


def test_move_images2(tmpdir):
    PROJECT_NAME = "test move folder images2"
    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(PROJECT_NAME, return_metadata=True)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(PROJECT_NAME, 'test', 'Vector')
    sa.create_folder(project, "folder1")
    project = PROJECT_NAME + "/folder1"
    sa.upload_images_from_folder_to_project(
        project, FROM_FOLDER, annotation_status="InProgress"
    )
    num_images = sa.get_project_image_count(project)
    assert num_images == 4

    sa.create_folder(PROJECT_NAME, "folder2")
    project2 = PROJECT_NAME + "/folder2"
    num_images = sa.get_project_image_count(project2)
    assert num_images == 0

    sa.move_images(project, project2)

    num_images = sa.get_project_image_count(project2)
    assert num_images == 4

    num_images = sa.get_project_image_count(project)
    assert num_images == 0


def test_copy_images2(tmpdir):
    PROJECT_NAME = "test copy folder annotation images"
    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(PROJECT_NAME, return_metadata=True)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(PROJECT_NAME, 'test', 'Vector')
    sa.create_annotation_classes_from_classes_json(
        project, FROM_FOLDER / "classes" / "classes.json"
    )
    sa.create_folder(project, "folder1")
    project = PROJECT_NAME + "/folder1"
    sa.upload_images_from_folder_to_project(
        project, FROM_FOLDER, annotation_status="InProgress"
    )

    sa.upload_annotations_from_folder_to_project(project, FROM_FOLDER)
    num_images = sa.get_project_image_count(project)
    assert num_images == 4

    sa.create_folder(PROJECT_NAME, "folder2")
    project2 = PROJECT_NAME + "/folder2"
    num_images = sa.get_project_image_count(project2)
    assert num_images == 0

    sa.pin_image(project, "example_image_2.jpg")

    im1 = sa.get_image_metadata(project, "example_image_2.jpg")
    assert im1["is_pinned"] == 1
    assert im1["annotation_status"] == "InProgress"

    sa.copy_images(
        project, project2, ["example_image_2.jpg", "example_image_3.jpg"]
    )

    num_images = sa.get_project_image_count(project2)
    assert num_images == 2

    ann1 = sa.get_image_annotations(project, "example_image_2.jpg")
    ann2 = sa.get_image_annotations(project2, "example_image_2.jpg")
    assert ann1 == ann2

    im1_copied = sa.get_image_metadata(project2, "example_image_2.jpg")
    assert im1_copied["is_pinned"] == 1
    assert im1_copied["annotation_status"] == "InProgress"

    im2_copied = sa.get_image_metadata(project2, "example_image_3.jpg")
    assert im2_copied["is_pinned"] == 0
    assert im2_copied["annotation_status"] == "InProgress"


def test_folder_export(tmpdir):
    PROJECT_NAME = "test folder export"
    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(PROJECT_NAME, return_metadata=True)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(PROJECT_NAME, 'test', 'Vector')
    sa.create_annotation_classes_from_classes_json(
        project, FROM_FOLDER / "classes" / "classes.json"
    )
    sa.upload_images_from_folder_to_project(
        project, FROM_FOLDER, annotation_status="InProgress"
    )
    sa.create_folder(project, "folder1")
    project = PROJECT_NAME + "/folder1"
    sa.upload_images_from_folder_to_project(
        project, FROM_FOLDER, annotation_status="InProgress"
    )

    sa.upload_annotations_from_folder_to_project(project, FROM_FOLDER)
    num_images = sa.get_project_image_count(project)
    assert num_images == 4

    sa.create_folder(PROJECT_NAME, "folder2")
    project2 = PROJECT_NAME + "/folder2"
    num_images = sa.get_project_image_count(project2)
    assert num_images == 0

    sa.copy_images(
        project, project2, ["example_image_2.jpg", "example_image_3.jpg"]
    )

    export = sa.prepare_export(PROJECT_NAME, ["folder1", "folder2"])
    sa.download_export(project, export, tmpdir)

    assert len(list((tmpdir / "classes").rglob("*"))) == 1

    assert len(list((tmpdir / "folder1").rglob("*"))) == 4

    assert len(list((tmpdir / "folder2").rglob("*"))) == 2

    assert len(list((tmpdir).glob("*.*"))) == 0

    export = sa.prepare_export(PROJECT_NAME)
    sa.download_export(project, export, tmpdir)

    assert len(list((tmpdir / "classes").rglob("*"))) == 1

    assert len(list((tmpdir / "folder1").rglob("*"))) == 4

    assert len(list((tmpdir / "folder2").rglob("*"))) == 2

    assert len(list((tmpdir).glob("*.*"))) == 4


def test_folder_image_annotation_status(tmpdir):
    PROJECT_NAME = "test folder set annotation status"
    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(PROJECT_NAME, return_metadata=True)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(PROJECT_NAME, 'test', 'Vector')
    sa.create_annotation_classes_from_classes_json(
        project, FROM_FOLDER / "classes" / "classes.json"
    )
    sa.upload_images_from_folder_to_project(
        project, FROM_FOLDER, annotation_status="InProgress"
    )
    sa.create_folder(project, "folder1")
    project = PROJECT_NAME + "/folder1"
    sa.upload_images_from_folder_to_project(
        project, FROM_FOLDER, annotation_status="InProgress"
    )

    sa.set_images_annotation_statuses(
        project, ["example_image_1.jpg", "example_image_2.jpg"], "QualityCheck"
    )

    for image in ["example_image_1.jpg", "example_image_2.jpg"]:
        metadata = sa.get_image_metadata(project, image)
        assert metadata["annotation_status"] == "QualityCheck"

    for image in ["example_image_3.jpg", "example_image_3.jpg"]:
        metadata = sa.get_image_metadata(project, image)
        assert metadata["annotation_status"] == "InProgress"

    sa.set_images_annotation_statuses(PROJECT_NAME, None, "QualityCheck")

    for image in sa.search_images(PROJECT_NAME):
        metadata = sa.get_image_metadata(PROJECT_NAME, image)
        assert metadata["annotation_status"] == "QualityCheck"


def test_folder_misnamed(tmpdir):
    PROJECT_NAME = "test folder misnamed"
    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(PROJECT_NAME, return_metadata=True)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(PROJECT_NAME, 'test', 'Vector')
    sa.create_folder(project, "folder1")
    assert "folder1" in sa.search_folders(project)

    sa.create_folder(project, "folder1")
    assert "folder1 (1)" in sa.search_folders(project)

    sa.create_folder(project, "folder2\\")
    assert "folder2_" in sa.search_folders(project)