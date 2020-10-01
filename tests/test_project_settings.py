from pathlib import Path
import time

import superannotate as sa

PROJECT_NAME = "test get set project settings"


def test_get_set_settings(tmpdir):
    tmpdir = Path(tmpdir)

    projects = sa.search_projects(PROJECT_NAME, return_metadata=True)
    for project in projects:
        sa.delete_project(project)

    sa.create_project(PROJECT_NAME, "tt", "Vector")

    old_settings = sa.get_project_settings(PROJECT_NAME)
    for setting in old_settings:
        if "attribute" in setting and setting["attribute"] == "Brightness":
            brightness_value = setting["value"]
    new_settings = sa.set_project_settings(
        PROJECT_NAME,
        [{
            "attribute": "Brightness",
            "value": brightness_value + 10
        }]
    )
    assert new_settings[0]["value"] == brightness_value + 10

    time.sleep(1)
    new_settings = sa.get_project_settings(PROJECT_NAME)
    for setting in new_settings:
        if "attribute" in setting and setting["attribute"] == "Brightness":
            new_brightness_value = setting["value"]

    assert new_brightness_value == brightness_value + 10
