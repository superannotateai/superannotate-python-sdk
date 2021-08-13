import time

import src.lib.app.superannotate as sa
from src.tests.integration.base import BaseTestCase


class TestProjectRename(BaseTestCase):
    PROJECT_NAME = "rename"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    NEW_PROJECT_NAME = "new"

    def test_project_rename(self):
        sa.rename_project(self.PROJECT_NAME, self.NEW_PROJECT_NAME)
        time.sleep(2)
        meta = sa.get_project_metadata(self.NEW_PROJECT_NAME)
        project = meta["project"]
        assert project["name"] == self.NEW_PROJECT_NAME
