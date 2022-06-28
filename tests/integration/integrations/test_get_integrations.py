import os
from os.path import dirname

import pytest
from src.superannotate import SAClient
sa = SAClient()
from tests.integration.base import BaseTestCase


class TestGetIntegrations(BaseTestCase):
    PROJECT_NAME = "TestGetIntegrations"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    TEST_FOLDER_NAME = "test_folder"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"
    EXAMPLE_IMAGE = "egit xample_image_1.jpg"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    def test_get(self):
        integrations = sa.get_integrations()
        integrations = sa.attach_items_from_integrated_storage(self.PROJECT_NAME, integrations[0]["name"])
