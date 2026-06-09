from src.superannotate import SAClient
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestTiledProject(BaseTestCase):
    PROJECT_NAME = "TestGetIntegrations"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Tiled"

    def test_get_metadata(self):
        self._attach_items()
        assert all(i["metadata"]["name"] for i in sa.get_annotations(self.PROJECT_NAME))
