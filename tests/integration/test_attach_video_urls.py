import os
from os.path import dirname

import src.superannotate as sa
from tests.integration.base import BaseTestCase


class TestVideoUrls(BaseTestCase):
    PROJECT_NAME = "test attach video urls"
    PATH_TO_URLS = "data_set/attach_urls.csv"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Video"

    def test_attach_image_urls(self):
        uploaded, could_not_upload, existing_images = sa.attach_video_urls_to_project(
            self.PROJECT_NAME,
            os.path.join(dirname(dirname(__file__)), self.PATH_TO_URLS),
        )
        self.assertEqual(len(uploaded), 8)
        self.assertEqual(len(could_not_upload), 0)
        self.assertEqual(len(existing_images), 0)
        images = sa.search_images(project=self.PROJECT_NAME, return_metadata=True)
        self.assertTrue(all([image["name"] for image in images]))
