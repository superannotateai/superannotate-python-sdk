from pathlib import Path
import time
import pytest
import superannotate as sa
from superannotate.api import API

_api = API.get_instance()


def safe_create_project(name, desc="test", p_type="Vector"):
    projects = sa.search_projects(name, return_metadata=True)
    for project in projects:
        sa.delete_project(project)
    time.sleep(1)
    project = sa.create_project(name, desc, p_type)
    time.sleep(4)
    return project


def test_assign_images():
    import datetime
    print("START TIME: ", datetime.datetime.now().strftime("%H:%M:%S"))
    PROJECT_NAME_VECTOR = "test_assign_images"

    project = safe_create_project(PROJECT_NAME_VECTOR, "test", "Vector")
    email = sa.get_team_metadata()["users"][0]["email"]
    sa.share_project(project, email, "QA")
    print("26: ", datetime.datetime.now().strftime("%H:%M:%S"))
    time.sleep(1)

    sa.upload_images_from_folder_to_project(
        project, "./tests/sample_project_vector"
    )
    print("32: ", datetime.datetime.now().strftime("%H:%M:%S"))
    time.sleep(2)

    sa.assign_images(
        project, ["example_image_1.jpg", "example_image_2.jpg"], email
    )
    print("38: ", datetime.datetime.now().strftime("%H:%M:%S"))
    time.sleep(3)
    im1_metadata = sa.get_image_metadata(project, "example_image_1.jpg")
    im2_metadata = sa.get_image_metadata(project, "example_image_2.jpg")
    print("42: ", datetime.datetime.now().strftime("%H:%M:%S"))
    assert im1_metadata["qa_id"] == email
    assert im2_metadata["qa_id"] == email

    sa.unshare_project(project, email)

    time.sleep(1)
    print("49: ", datetime.datetime.now().strftime("%H:%M:%S"))
    im1_metadata = sa.get_image_metadata(project, "example_image_1.jpg")
    im2_metadata = sa.get_image_metadata(project, "example_image_2.jpg")

    assert im1_metadata["qa_id"] is None
    assert im2_metadata["qa_id"] is None
    assert im1_metadata["annotator_id"] is None
    assert im2_metadata["annotator_id"] is None
    print("57: ", datetime.datetime.now().strftime("%H:%M:%S"))
    sa.share_project(project, email, "Annotator")

    sa.assign_images(
        project, ["example_image_1.jpg", "example_image_2.jpg"], email
    )
    print("63: ", datetime.datetime.now().strftime("%H:%M:%S"))
    time.sleep(1)
    im1_metadata = sa.get_image_metadata(project, "example_image_1.jpg")
    im2_metadata = sa.get_image_metadata(project, "example_image_2.jpg")

    assert im1_metadata["annotator_id"] == email
    assert im2_metadata["annotator_id"] == email
    assert im1_metadata["qa_id"] is None
    assert im2_metadata["qa_id"] is None


def test_assign_images_folder():
    PROJECT_NAME_VECTOR = "test_assign_images_folder_p"
    folder = "test_assign_images_folder"

    project = safe_create_project(PROJECT_NAME_VECTOR, "test", "Vector")
    email = sa.get_team_metadata()["users"][0]["email"]
    sa.share_project(project, email, "QA")
    sa.create_folder(project, folder)
    time.sleep(4)

    project_folder = project["name"] + "/" + folder

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

    time.sleep(2)

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


def test_un_assign_images():
    PROJECT_NAME_VECTOR = "test_un_assign_images"

    project = safe_create_project(PROJECT_NAME_VECTOR, "test", "Vector")
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
    FOLDER_NAME = "test_folder"
    sa.create_folder(project, FOLDER_NAME)
    project = PROJECT_NAME_VECTOR + "/" + FOLDER_NAME
    sa.move_images(
        PROJECT_NAME_VECTOR, ["example_image_1.jpg", "example_image_2.jpg"], project
    )
    sa.assign_images(
        project, ["example_image_1.jpg", "example_image_2.jpg"], email
    )
    time.sleep(1)
    sa.unassign_images(
        project,
        ["example_image_1.jpg", "example_image_2.jpg"],
    )

    sa.search_images(project)
    im1_metadata = sa.get_image_metadata(project, "example_image_1.jpg")

    im2_metadata = sa.get_image_metadata(project, "example_image_2.jpg")

    assert im1_metadata["qa_id"] == None
    assert im2_metadata["qa_id"] == None


def test_assign_folder():
    PROJECT_NAME_VECTOR = "test_assign_folder"

    project = safe_create_project(PROJECT_NAME_VECTOR, "test", "Vector")
    folder_name = "assign_folder"
    sa.create_folder(project, folder_name)
    email = sa.get_team_metadata()["users"][1]["email"]
    sa.share_project(project, email, "QA")
    time.sleep(2)
    sa.assign_folder(project, folder_name, [email])
    time.sleep(2)
    folders = _search_folders(project, includeUsers=True)
    assert len(folders["data"][0]['folder_users']) > 0


def test_un_assign_folder(tmpdir):
    PROJECT_NAME_VECTOR = "test_un_assign_folder"

    project = safe_create_project(PROJECT_NAME_VECTOR, "test", "Vector")
    folder_name = "assign_folder"
    time.sleep(1)
    sa.create_folder(project, folder_name)
    time.sleep(1)
    email = sa.get_team_metadata()["users"][1]["email"]
    time.sleep(1)
    sa.share_project(project, email, "QA")
    time.sleep(1)
    sa.assign_folder(project, folder_name, [email])
    time.sleep(1)
    folders = _search_folders(project, includeUsers=True)
    assert len(folders["data"][0]['folder_users']) > 0
    sa.unassign_folder(project, folder_name)
    time.sleep(1)

    folders = _search_folders(project, includeUsers=True)
    time.sleep(1)
    assert len(folders["data"][0]['folder_users']) == 0


def _search_folders(project, folder_name=None, includeUsers=False):
    team_id, project_id = project["team_id"], project["id"]
    params = {
        'team_id': team_id,
        'project_id': project_id,
        'offset': 0,
        'name': folder_name,
        'is_root': 0,
        'includeUsers': includeUsers
    }

    response = _api.send_request(req_type='GET', path='/folders', params=params)
    response = response.json()
    return response


def test_assign_folder_unverified_users(caplog):
    PROJECT_NAME_VECTOR = "test_assign_folder_unverified_users"

    project = safe_create_project(PROJECT_NAME_VECTOR, "test", "Vector")
    folder_name = "assign_folder"
    sa.create_folder(project, folder_name)
    email = "unverified_user@mail.com"
    try:
        sa.assign_folder(project, folder_name, [email])
    except:
        pass
    assert "Skipping unverified_user@mail.com from assignees." in caplog.text


def test_assign_images_unverified_user(caplog):
    PROJECT_NAME_VECTOR = "test_assign_images_unverified_user"

    project = safe_create_project(PROJECT_NAME_VECTOR, "test", "Vector")
    folder = "nfolder1"
    sa.create_folder(project, folder)
    project_folder = project["name"] + "/" + folder
    sa.upload_images_from_folder_to_project(
        project_folder, "./tests/sample_project_vector"
    )
    email = "unverified_user@email.com"
    try:
        sa.assign_images(
            project_folder, ["example_image_1.jpg", "example_image_2.jpg"],
            email
        )
    except:
        pass
    # assert "Skipping unverified_user@mail.com from assignees." in caplog.text
