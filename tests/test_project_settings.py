from pathlib import Path
import time

import superannotate as sa
from .test_assign_images import safe_create_project
PROJECT_NAME = "test get set project settings"


def test_get_set_settings(tmpdir):
    safe_create_project(PROJECT_NAME,"tt", "Vector")
    time.sleep(2)
    old_settings = sa.get_project_settings(PROJECT_NAME)

    print(old_settings)
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

    time.sleep(2)
    new_settings = sa.get_project_settings(PROJECT_NAME)
    for setting in new_settings:
        if "attribute" in setting and setting["attribute"] == "Brightness":
            new_brightness_value = setting["value"]

    assert new_brightness_value == brightness_value + 10
