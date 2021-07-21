import time

import superannotate as sa
from .test_assign_images import safe_create_project




def test_create_from_full_info():
    PROJECT_NAME1 = "test create from full info1"
    PROJECT_NAME2 = "test create from full info2"

    project = safe_create_project(PROJECT_NAME1,"test","Vector")

    sa.upload_images_from_folder_to_project(
        project, "./tests/sample_project_vector"
    )
    sa.create_annotation_classes_from_classes_json(
        project, "./tests/sample_project_vector/classes/classes.json"
    )
    time.sleep(2)
    old_settings = sa.get_project_settings(PROJECT_NAME1)

    for setting in old_settings:
        if "attribute" in setting and setting["attribute"] == "Brightness":
            brightness_value = setting["value"]
    sa.set_project_settings(
        PROJECT_NAME1,
        [{
            "attribute": "Brightness",
            "value": brightness_value + 10
        }]
    )
    team_users = sa.search_team_contributors()

    sa.share_project(PROJECT_NAME1, team_users[1], "QA")

    project_metadata = sa.get_project_metadata(
        project,
        include_annotation_classes=True,
        include_settings=True,
        include_workflow=True,
        include_contributors=True
    )

    project_metadata["name"] = PROJECT_NAME2

    print(project_metadata)
    projects = sa.search_projects(PROJECT_NAME2, return_metadata=True)
    for project in projects:
        sa.delete_project(project)
    time.sleep(2)
    sa.create_project_from_metadata(project_metadata)
    time.sleep(2)
    new_project_metadata = sa.get_project_metadata(
        PROJECT_NAME2,
        include_annotation_classes=True,
        include_settings=True,
        include_workflow=True,
        include_contributors=True
    )

    for u in new_project_metadata["contributors"]:
        if u["user_id"] == team_users[1]:
            break
    else:
        assert False

    assert len(new_project_metadata["annotation_classes"]) == len(
        project_metadata["annotation_classes"]
    )

    assert len(new_project_metadata["settings"]) == len(
        project_metadata["settings"]
    )
    for new_setting in new_project_metadata["settings"]:
        if "attribute" in new_setting and new_setting["attribute"
                                                     ] == "Brightness":
            new_brightness_value = new_setting["value"]
    assert new_brightness_value == brightness_value + 10

    assert len(new_project_metadata['workflow']) == len(
        project_metadata["workflow"]
    )
