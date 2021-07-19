import time
from pathlib import Path
import pytest
import superannotate as sa
from .test_assign_images import safe_create_project

sa.init(Path.home() / ".superannotate" / "config.json")

PROJECT_NAME = "test rename_project"
PROJECT_NAME_NEW = "test rename_project new"


def test_project_rename():

    safe_create_project(PROJECT_NAME,'tt')
    projects = sa.search_projects(PROJECT_NAME_NEW, return_metadata=True)
    for project in projects:
        sa.delete_project(project)
    time.sleep(2)
    sa.rename_project(PROJECT_NAME, PROJECT_NAME_NEW)
    time.sleep(2)
    sa.get_project_metadata(PROJECT_NAME_NEW)
    with pytest.raises(sa.SAExistingProjectNameException):
        sa.rename_project(PROJECT_NAME_NEW, PROJECT_NAME_NEW)
