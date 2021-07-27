import os
import time
from os.path import dirname
from unittest import TestCase

import src.lib.app.superannotate as sa


class TestAnnotationClasses(TestCase):
    PROJECT_NAME = "test attach image urls"
    PATH_TO_URLS = "data_set/attach_urls.csv"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"

    @classmethod
    def setUp(cls):
        cls.tearDownClass()
        time.sleep(2)
        cls._project = sa.create_project(
            cls.PROJECT_NAME, cls.PROJECT_DESCRIPTION, cls.PROJECT_TYPE
        )

    @classmethod
    def tearDownClass(cls) -> None:
        projects = sa.search_projects(cls.PROJECT_NAME, return_metadata=True)
        for project in projects:
            sa.delete_project(project)

    def test_attach_image_urls(self):
        uploaded, could_not_upload, existing_images = sa.attach_image_urls_to_project(
            self.PROJECT_NAME,
            os.path.join(dirname(dirname(__file__)), self.PATH_TO_URLS),
        )
        self.assertEqual(len(uploaded), 8)
        self.assertEqual(len(could_not_upload), 0)
        self.assertEqual(len(existing_images), 0)
