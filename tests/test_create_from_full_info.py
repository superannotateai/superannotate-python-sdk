from pathlib import Path

import superannotate as sa

import pytest

PROJECT_NAME1 = "test create from full info1"
PROJECT_NAME2 = "test create from full info2"


def test_create_from_full_info(tmpdir):
    tmpdir = Path(tmpdir)

    projects = sa.search_projects(PROJECT_NAME1, return_metadata=True)
    for project in projects:
        sa.delete_project(project)

    project = sa.create_project(PROJECT_NAME1, "test", "Vector")

    sa.upload_images_from_folder_to_project(
        project, "./tests/sample_project_vector"
    )
    sa.create_annotation_classes_from_classes_json(
        project, "./tests/sample_project_vector/classes/classes.json"
    )
    old_settings = sa.get_project_settings(PROJECT_NAME1)
    for setting in old_settings:
        if "attribute" in setting and setting["attribute"] == "Brightness":
            brightness_value = setting["value"]
    new_settings = sa.set_project_settings(
        PROJECT_NAME1,
        [{
            "attribute": "Brightness",
            "value": brightness_value + 10
        }]
    )
    team_users = sa.search_team_contributors()

    sa.share_project(PROJECT_NAME1, team_users[1], "QA")

    project_metadata, annotation_classes, users, settings, workflow = sa.get_project_full_info(
        project
    )

    project_metadata["name"] = PROJECT_NAME2

    print(project_metadata)
    projects = sa.search_projects(PROJECT_NAME2, return_metadata=True)
    for project in projects:
        sa.delete_project(project)
    sa.create_project_from_full_info(
        project_metadata, annotation_classes, users, settings, workflow
    )
    new_project_metadata, new_annotation_classes, new_users, new_settings, new_workflow = sa.get_project_full_info(
        PROJECT_NAME2
    )

    for u in new_users:
        if u["user_id"] == team_users[1]:
            break
    else:
        assert False

    assert len(new_annotation_classes) == len(annotation_classes)

    assert len(new_settings) == len(settings)
    for new_setting in new_settings:
        if "attribute" in new_setting and new_setting["attribute"
                                                     ] == "Brightness":
            new_brightness_value = new_setting["value"]
    assert new_brightness_value == brightness_value + 10

    assert len(new_workflow) == len(workflow)
