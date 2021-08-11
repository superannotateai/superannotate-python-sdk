import src.lib.app.superannotate as sa
from src.tests.integration.base import BaseTestCase


class TestProjectSettings(BaseTestCase):
    PROJECT_NAME = "settings"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"

    def test_project_settings(self):
        old_settings = sa.get_project_settings(self.PROJECT_NAME)
        brightness_value = 0
        for setting in old_settings:
            if "attribute" in setting and setting["attribute"] == "Brightness":
                brightness_value = setting["value"]
        new_settings = sa.set_project_settings(
            self.PROJECT_NAME,
            [{"attribute": "Brightness", "value": brightness_value + 10}],
        )
        assert new_settings[0]["value"] == brightness_value + 10
