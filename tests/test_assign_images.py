from pathlib import Path
import time

import pytest

import superannotate as sa

PROJECT_NAME_VECTOR1 = "test assign images1"
PROJECT_NAME_VECTOR2 = "test assign images2"
FOLDER2 = "folder2"


def test_assign_images(tmpdir):
    tmpdir = Path(tmpdir)

    projects = sa.search_projects(PROJECT_NAME_VECTOR1, return_metadata=True)
    for project in projects:
        sa.delete_project(project)
    time.sleep(1)
    project = sa.create_project(PROJECT_NAME_VECTOR1, "test", "Vector")
    email = sa.get_team_metadata()["users"][0]["email"]
    sa.share_project(project, email, "QA")

    sa.upload_images_from_folder_to_project(
        project, "./tests/sample_project_vector"
    )

    sa.assign_images(
        project, ["example_image_1.jpg", "example_image_2.jpg"], email
    )

    time.sleep(1)
    im1_metadata = sa.get_image_metadata(project, "example_image_1.jpg")
    im2_metadata = sa.get_image_metadata(project, "example_image_2.jpg")

    assert im1_metadata["qa_id"] == email
    assert im2_metadata["qa_id"] == email

    sa.unshare_project(project, email)

    time.sleep(1)

    im1_metadata = sa.get_image_metadata(project, "example_image_1.jpg")
    im2_metadata = sa.get_image_metadata(project, "example_image_2.jpg")

    assert im1_metadata["qa_id"] is None
    assert im2_metadata["qa_id"] is None
    assert im1_metadata["annotator_id"] is None
    assert im2_metadata["annotator_id"] is None

    sa.share_project(project, email, "Annotator")

    sa.assign_images(
        project, ["example_image_1.jpg", "example_image_2.jpg"], email
    )

    time.sleep(1)
    im1_metadata = sa.get_image_metadata(project, "example_image_1.jpg")
    im2_metadata = sa.get_image_metadata(project, "example_image_2.jpg")

    assert im1_metadata["annotator_id"] == email
    assert im2_metadata["annotator_id"] == email
    assert im1_metadata["qa_id"] is None
    assert im2_metadata["qa_id"] is None


def test_assign_images_folder(tmpdir):
    tmpdir = Path(tmpdir)

    projects = sa.search_projects(PROJECT_NAME_VECTOR2, return_metadata=True)
    for project in projects:
        sa.delete_project(project)
    time.sleep(1)
    project = sa.create_project(PROJECT_NAME_VECTOR2, "test", "Vector")
    email = sa.get_team_metadata()["users"][0]["email"]
    sa.share_project(project, email, "QA")
    sa.create_folder(project, FOLDER2)

    project_folder = project["name"] + "/" + FOLDER2

    sa.upload_images_from_folder_to_project(
        project_folder, "./tests/sample_project_vector"
    )

    sa.assign_images(
        project_folder, ["example_image_1.jpg", "example_image_2.jpg"], email
    )

    time.sleep(1)
    im1_metadata = sa.get_image_metadata(project_folder, "example_image_1.jpg")
    im2_metadata = sa.get_image_metadata(project_folder, "example_image_2.jpg")

    assert im1_metadata["qa_id"] == email
    assert im2_metadata["qa_id"] == email

    sa.unshare_project(project, email)

    time.sleep(1)

    im1_metadata = sa.get_image_metadata(project_folder, "example_image_1.jpg")
    im2_metadata = sa.get_image_metadata(project_folder, "example_image_2.jpg")

    assert im1_metadata["qa_id"] is None
    assert im2_metadata["qa_id"] is None
    assert im1_metadata["annotator_id"] is None
    assert im2_metadata["annotator_id"] is None

    sa.share_project(project, email, "Annotator")

    sa.assign_images(
        project_folder, ["example_image_1.jpg", "example_image_2.jpg"], email
    )

    time.sleep(1)
    im1_metadata = sa.get_image_metadata(project_folder, "example_image_1.jpg")
    im2_metadata = sa.get_image_metadata(project_folder, "example_image_2.jpg")

    assert im1_metadata["annotator_id"] == email
    assert im2_metadata["annotator_id"] == email
    assert im1_metadata["qa_id"] is None
    assert im2_metadata["qa_id"] is None


def test_unassign_images(tmpdir):
    tmpdir = Path(tmpdir)
    projects = sa.search_projects(PROJECT_NAME_VECTOR1, return_metadata=True)
    for project in projects:
        sa.delete_project(project)
    time.sleep(1)
    project = sa.create_project(PROJECT_NAME_VECTOR1, "test", "Vector")
    email = sa.get_team_metadata()["users"][0]["email"]
    sa.share_project(project, email, "QA")
    sa.upload_images_from_folder_to_project(
        project, "./tests/sample_project_vector"
    )
    sa.assign_images(
        project, ["example_image_1.jpg", "example_image_2.jpg"], email
    )
    sa.unassign_images(
        project,
        ["example_image_1.jpg", "example_image_2.jpg"],
    )

    im1_metadata = sa.get_image_metadata(project, "example_image_1.jpg")
    im2_metadata = sa.get_image_metadata(project, "example_image_2.jpg")

    assert im1_metadata["qa_id"] == None
    assert im2_metadata["qa_id"] == None


def test_assign_folder(tmpdir):
    tmpdir = Path(tmpdir)
    projects = sa.search_projects(PROJECT_NAME_VECTOR1, return_metadata=True)
    for project in projects:
        sa.delete_project(project)
    time.sleep(1)
    project = sa.create_project(PROJECT_NAME_VECTOR1, "test", "Vector")
    folder_name = "assign_folder"
    sa.create_folder(project, folder_name)
    email = sa.get_team_metadata()["users"][1]["email"]
    sa.share_project(project, email, "QA")
    sa.assign_folder(project, folder_name, [email])
    folders = sa._search_folders(PROJECT_NAME_VECTOR1, includeUsers=True)
    assert len(folders["data"][0]['folder_users']) > 0


def test_unassign_folder(tmpdir):
    tmpdir = Path(tmpdir)
    projects = sa.search_projects(PROJECT_NAME_VECTOR1, return_metadata=True)
    for project in projects:
        sa.delete_project(project)
    time.sleep(1)
    project = sa.create_project(PROJECT_NAME_VECTOR1, "test", "Vector")
    folder_name = "assign_folder"
    sa.create_folder(project, folder_name)
    email = sa.get_team_metadata()["users"][1]["email"]
    sa.share_project(project, email, "QA")
    sa.assign_folder(project, folder_name, [email])
    folders = sa._search_folders(PROJECT_NAME_VECTOR1, includeUsers=True)
    assert len(folders["data"][0]['folder_users']) > 0
    sa.unassign_folder(project, folder_name)
    folders = sa._search_folders(PROJECT_NAME_VECTOR1, includeUsers=True)
    assert len(folders["data"][0]['folder_users']) == 0
