import os
from os.path import dirname

import src.superannotate as sa
from tests.integration.base import BaseTestCase


class TestDocumentUrls(BaseTestCase):
    PROJECT_NAME = "document attach urls"
    PATH_TO_URLS = "data_set/csv_files/text_urls.csv"
    PATH_TO_50K_URLS = "data_set/501_urls.csv"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Document"

    def test_attach_documents_urls(self):
        uploaded, could_not_upload, existing_images = sa.attach_document_urls_to_project(
            self.PROJECT_NAME,
            os.path.join(dirname(dirname(__file__)), self.PATH_TO_URLS),
        )
        self.assertEqual(len(uploaded), 11)
        self.assertEqual(len(could_not_upload), 0)
        self.assertEqual(len(existing_images), 1)

        uploaded, could_not_upload, existing_images = sa.attach_document_urls_to_project(
            self.PROJECT_NAME,
            os.path.join(dirname(dirname(__file__)), self.PATH_TO_URLS),
        )
        self.assertEqual(len(uploaded), 2)
        self.assertEqual(len(could_not_upload), 0)
        self.assertEqual(len(existing_images), 10)


    def test_limitation(self):
        self.assertRaises(
            Exception,
            sa.attach_document_urls_to_project,
            self.PROJECT_NAME,
            os.path.join(dirname(dirname(__file__)), self.PATH_TO_50K_URLS)
        )