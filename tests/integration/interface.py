import src.superannotate as sa
from tests.integration.base import BaseTestCase


class TestInterface(BaseTestCase):
    PROJECT_NAME = "Interface test"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"

    def test_get_project_default_image_quality_in_editor(self):
        self.assertIsNotNone(sa.get_project_default_image_quality_in_editor(self.PROJECT_NAME))
