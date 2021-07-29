import os
from os.path import dirname

import src.lib.app.superannotate as sa
from src.tests.integration.base import BaseTestCase


class TestAnnotationClasses(BaseTestCase):
    PROJECT_NAME = "test attach image urls"
    PATH_TO_URLS = "data_set/attach_urls.csv"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"

    def test_attach_image_urls(self):
        uploaded, could_not_upload, existing_images = sa.attach_image_urls_to_project(
            self.PROJECT_NAME,
            os.path.join(dirname(dirname(__file__)), self.PATH_TO_URLS),
        )
        self.assertEqual(len(uploaded), 8)
        self.assertEqual(len(could_not_upload), 0)
        self.assertEqual(len(existing_images), 0)
