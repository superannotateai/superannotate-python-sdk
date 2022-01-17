import os
import pytest
from os.path import dirname

import src.superannotate as sa
from src.superannotate.lib.core import UploadState
from src.superannotate.lib.core.exceptions import AppException
from tests.integration.base import BaseTestCase


class TestImageUrls(BaseTestCase):
    PROJECT_NAME = "test attach image urls"
    PATH_TO_URLS = "data_set/attach_urls.csv"
    PATH_TO_50K_URLS = "data_set/501_urls.csv"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"

    @pytest.mark.flaky(reruns=2)
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
        truth = {'name': '',
         'path': 'https://drive.google.com/uc?export=download&id=1geS2YtQiTYuiduEirKVYxBujHJaIWA3V',
         'annotation_status': 'NotStarted', 'prediction_status': None, 'segmentation_status': None,
         'approval_status': None, 'is_pinned': 0, 'annotator_name': None, 'qa_name': None, 'entropy_value': None,
         'createdAt': '', 'updatedAt': ''}
        image = images[0]
        image['createdAt'] = ''
        image['updatedAt'] = ''
        image['name'] = ''
        self.assertEqual(image, truth)

    def test_double_attach_image_urls(self):
        uploaded, could_not_upload, existing_images = sa.attach_image_urls_to_project(
            self.PROJECT_NAME,
            os.path.join(dirname(dirname(__file__)), self.PATH_TO_URLS),
        )
        self.assertEqual(len(uploaded), 7)
        self.assertEqual(len(could_not_upload), 0)
        self.assertEqual(len(existing_images), 1)

        uploaded, could_not_upload, existing_images = sa.attach_image_urls_to_project(
            self.PROJECT_NAME,
            os.path.join(dirname(dirname(__file__)), self.PATH_TO_URLS),
        )
        self.assertEqual(len(uploaded), 2)
        self.assertEqual(len(could_not_upload), 0)
        self.assertEqual(len(existing_images), 6)

    def test_limitation(self):
        self.assertRaises(
            Exception,
            sa.attach_image_urls_to_project,
            self.PROJECT_NAME,
            os.path.join(dirname(dirname(__file__)), self.PATH_TO_50K_URLS)
        )
