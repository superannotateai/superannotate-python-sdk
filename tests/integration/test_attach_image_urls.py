import os
from os.path import dirname

import src.superannotate as sa
from src.superannotate.lib.core import UploadState
from tests.integration.base import BaseTestCase


class TestImageUrls(BaseTestCase):
    PROJECT_NAME = "test attach image urls"
    PATH_TO_URLS = "data_set/attach_urls.csv"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"

    def test_attach_image_urls(self):
        uploaded, could_not_upload, existing_images = sa.attach_image_urls_to_project(
            self.PROJECT_NAME,
            os.path.join(dirname(dirname(__file__)), self.PATH_TO_URLS),
        )
        project_metadata = sa.get_project_metadata(self.PROJECT_NAME)

        self.assertEqual(UploadState.EXTERNAL.name, project_metadata["upload_state"])

        self.assertEqual(len(uploaded), 7)
        self.assertEqual(len(could_not_upload), 0)
        self.assertEqual(len(existing_images), 1)
        images = sa.search_images(project=self.PROJECT_NAME, return_metadata=True)
        self.assertTrue(all([image["name"] for image in images]))
