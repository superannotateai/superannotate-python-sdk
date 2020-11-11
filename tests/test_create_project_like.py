from pathlib import Path
import time

import superannotate as sa

PROJECT_NAME = "test create like project from"
PROJECT_NAME2 = "test create like project to"


def test_create_like_project(tmpdir):
    tmpdir = Path(tmpdir)

    projects = sa.search_projects(PROJECT_NAME, return_metadata=True)
    for project in projects:
        sa.delete_project(project)

    sa.create_project(PROJECT_NAME, "tt", "Vector")
    sa.create_annotation_class(PROJECT_NAME, "rrr", "#FFAAFF")

    old_settings = sa.get_project_settings(PROJECT_NAME)
    for setting in old_settings:
        if "attribute" in setting and setting["attribute"] == "Brightness":
            brightness_value = setting["value"]
    sa.set_project_settings(
        PROJECT_NAME,
        [{
            "attribute": "Brightness",
            "value": brightness_value + 10
        }]
    )
    sa.set_project_workflow(
        PROJECT_NAME, [{
            "step": 1,
            "className": "rrr",
            "tool": 3
        }]
    )
    users = sa.search_team_contributors()
    sa.share_project(PROJECT_NAME, users[1], "QA")

    projects = sa.search_projects(PROJECT_NAME2, return_metadata=True)
    for project in projects:
        sa.delete_project(project)

    new_project = sa.clone_project(
        PROJECT_NAME2, PROJECT_NAME, copy_project_contributors=True
    )
    assert new_project["description"] == "tt"
    assert new_project["type"] == 1
    time.sleep(1)

    ann_classes = sa.search_annotation_classes(
        PROJECT_NAME2, return_metadata=True
    )
    assert len(ann_classes) == 1
    assert ann_classes[0]["name"] == "rrr"
    assert ann_classes[0]["color"] == "#FFAAFF"

    new_settings = sa.get_project_settings(PROJECT_NAME2)
    for setting in new_settings:
        if "attribute" in setting and setting["attribute"] == "Brightness":
            new_brightness_value = setting["value"]

    assert new_brightness_value == brightness_value + 10

    new_workflow = sa.get_project_workflow(PROJECT_NAME2)
    assert len(new_workflow) == 1
    assert new_workflow[0]["className"] == "rrr"
    assert new_workflow[0]["tool"] == 3

    new_project = sa.get_project_metadata(new_project["name"])
    assert len(new_project["users"]) == 1
    assert new_project["users"][0]["user_id"] == users[1]
    assert new_project["users"][0]["user_role"] == sa.user_role_str_to_int("QA")
