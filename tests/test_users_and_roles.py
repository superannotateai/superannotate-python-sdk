from pathlib import Path

import superannotate as sa

sa.init(Path.home() / ".superannotate" / "config.json")


def test_users_roles():
    users = sa.search_team_contributors()

    project = sa.create_project("test_56", "test_56", 1)
    sa.share_project(project, users[1], 4)
    project_users = sa.get_project_metadata(project)["users"]
    found = False
    for u in project_users:
        if u["user_id"] == users[1]["id"]:
            found = True
            break
    assert found, users[1]

    sa.unshare_project(project, users[1])
    project_users = sa.get_project_metadata(project)["users"]
    found = False
    for u in project_users:
        if u["user_id"] == users[1]["id"]:
            found = True
            break
    assert not found, users[1]
