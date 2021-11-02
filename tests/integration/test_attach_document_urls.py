import os
from os.path import dirname
from os.path import join

import src.superannotate as sa
from src.superannotate import AppException
import src.superannotate.lib.core as constances
from tests.integration.base import BaseTestCase


class TestDocumentUrls(BaseTestCase):
    PROJECT_NAME = "document attach urls"
    PATH_TO_URLS = "csv_files/text_urls.csv"
    PATH_TO_50K_URLS = "501_urls.csv"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Document"

    @property
    def csv_path(self):
        return os.path.join(dirname(dirname(__file__)), "data_set")

    def test_attach_documents_urls(self):
        uploaded, could_not_upload, existing_images = sa.attach_document_urls_to_project(
            self.PROJECT_NAME,
            join(self.csv_path, self.PATH_TO_URLS)
        )
        self.assertEqual(len(uploaded), 11)
        self.assertEqual(len(could_not_upload), 0)
        self.assertEqual(len(existing_images), 1)

        uploaded, could_not_upload, existing_images = sa.attach_document_urls_to_project(
            self.PROJECT_NAME,
            join(self.csv_path, self.PATH_TO_URLS),
        )
        self.assertEqual(len(uploaded), 2)
        self.assertEqual(len(could_not_upload), 0)
        self.assertEqual(len(existing_images), 10)

    def test_attach_video_urls_to_vector_project(self):
        try:
            sa.create_project("1", "!", "vector")
            with self.assertRaisesRegexp(AppException, constances.INVALID_PROJECT_TYPE_TO_PROCESS.format("Vector")):
                sa.attach_document_urls_to_project("1", join(self.csv_path, self.PATH_TO_URLS),)
        except AssertionError:
            raise
        except Exception:
            sa.delete_project("1")

    def test_limitation(self):
        self.assertRaises(
            Exception,
            sa.attach_document_urls_to_project,
            self.PROJECT_NAME,
            join(self.csv_path, self.PATH_TO_50K_URLS)
        )