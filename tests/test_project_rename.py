from pathlib import Path
import pytest
import superannotate as sa

sa.init(Path.home() / ".superannotate" / "config.json")

PROJECT_NAME = "test rename_project"
PROJECT_NAME_NEW = "test rename_project new"


def test_project_rename():
    projects = sa.search_projects(PROJECT_NAME, return_metadata=True)
    for project in projects:
        sa.delete_project(project)

    sa.create_project(PROJECT_NAME, "tt", "Vector")
    projects = sa.search_projects(PROJECT_NAME_NEW, return_metadata=True)
    for project in projects:
        sa.delete_project(project)

    sa.rename_project(PROJECT_NAME, PROJECT_NAME_NEW)
    sa.get_project_metadata(PROJECT_NAME_NEW)

    with pytest.raises(sa.SAExistingProjectNameException):
        sa.rename_project(PROJECT_NAME_NEW, PROJECT_NAME_NEW)
