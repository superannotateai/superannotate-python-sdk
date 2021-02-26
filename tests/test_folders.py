from pathlib import Path
import json
from superannotate.exceptions import SABaseException

import pytest

import superannotate as sa

PROJECT_NAME1 = "test folder simple"
FROM_FOLDER = "./tests/sample_project_vector"


def test_basic_folders(tmpdir):
    tmpdir = Path(tmpdir)

    projects_found = sa.search_projects(PROJECT_NAME1, return_metadata=True)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(PROJECT_NAME1, 'test', 'Vector')
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

    images = sa.search_images(project, "example_image_1", folder="folder1")
    assert len(images) == 0

    folder = sa.get_folder_metadata(project, "folder1")
    assert isinstance(folder, dict)
    assert folder["name"] == "folder1"

    with pytest.raises(SABaseException) as e:
        folder = sa.get_folder_metadata(project, "folder2")
    assert 'Folder not found' in str(e)