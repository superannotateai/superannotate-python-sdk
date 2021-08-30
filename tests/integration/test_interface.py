import os
from os.path import dirname
import src.superannotate as sa
from tests.integration.base import BaseTestCase


class TestInterface(BaseTestCase):
    PROJECT_NAME = "Interface test"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"
    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    def test_get_project_default_image_quality_in_editor(self):
        sa.invite_contributor_to_team(2, 2)
        self.assertIsNotNone(sa.get_project_default_image_quality_in_editor(self.PROJECT_NAME))

    def test_get_project_metadata(self):
        pass
