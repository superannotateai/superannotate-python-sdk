import time
from pathlib import Path

import superannotate as sa

PROJECT_NAME = "test users and roles"


def test_users_roles():
    projects = sa.search_projects(PROJECT_NAME, return_metadata=True)
    for project in projects:
        sa.delete_project(project)
    users = sa.search_team_contributors()
    time.sleep(2)
    project = sa.create_project(PROJECT_NAME, "test_56", "Vector")
    time.sleep(2)
    sa.share_project(PROJECT_NAME, users[1], "QA")
    project_users = sa.get_project_metadata(
        PROJECT_NAME, include_contributors=True
    )["contributors"]
    print(project_users)
    found = False
    for u in project_users:
        if u["user_id"] == users[1]:
            found = True
            break
    assert found, users[1]

    sa.unshare_project(PROJECT_NAME, users[1])
    time.sleep(2)
    project_users = sa.get_project_metadata(
        PROJECT_NAME, include_contributors=True
    )["contributors"]
    found = False
    for u in project_users:
        if u["user_id"] == users[1]:
            found = True
            break
    assert not found, users[1]
