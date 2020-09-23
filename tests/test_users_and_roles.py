from pathlib import Path

import superannotate as sa

sa.init(Path.home() / ".superannotate" / "config.json")

PROJECT_NAME = "test users and roles"


def test_users_roles():
    projects = sa.search_projects(
        PROJECT_NAME, return_metadata=True, exact_match=True
    )
    for project in projects:
        sa.delete_project(project)
    users = sa.search_team_contributors()

    project = sa.create_project(PROJECT_NAME, "test_56", "Vector")
    sa.share_project(PROJECT_NAME, users[1], "QA")
    project_users = sa.get_project_metadata(PROJECT_NAME)["users"]
    print(project_users)
    found = False
    for u in project_users:
        if u["user_id"] == users[1]:
            found = True
            break
    assert found, users[1]

    sa.unshare_project(PROJECT_NAME, users[1])
    project_users = sa.get_project_metadata(PROJECT_NAME)["users"]
    found = False
    for u in project_users:
        if u["user_id"] == users[1]:
            found = True
            break
    assert not found, users[1]
