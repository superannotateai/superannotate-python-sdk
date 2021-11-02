import os
from os.path import dirname

import src.superannotate as sa
from src.superannotate import AppException
import src.superannotate.lib.core as constances
from tests.integration.base import BaseTestCase


class TestVideoUrls(BaseTestCase):
    PROJECT_NAME = "test attach video urls"
    PATH_TO_URLS = "data_set/attach_urls.csv"
    PATH_TO_URLS_WITHOUT_NAMES = "data_set/attach_urls_with_no_name.csv"
    PATH_TO_50K_URLS = "data_set/501_urls.csv"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Video"

    @property
    def csv_path(self):
        return os.path.join(dirname(dirname(__file__)), self.PATH_TO_URLS)

    @property
    def csv_path_without_name_column(self):
        return os.path.join(dirname(dirname(__file__)), self.PATH_TO_URLS_WITHOUT_NAMES)

    def test_attach_video_urls(self):
        uploaded, could_not_upload, existing_images = sa.attach_video_urls_to_project(
            self.PROJECT_NAME,
            self.csv_path,
        )
        self.assertEqual(len(uploaded), 7)
        self.assertEqual(len(could_not_upload), 0)
        self.assertEqual(len(existing_images), 1)

    def test_attach_video_urls_to_vector_project(self):
        try:
            sa.create_project("1", "!", "vector")
            with self.assertRaisesRegexp(AppException, constances.INVALID_PROJECT_TYPE_TO_PROCESS.format("Vector")):
                sa.attach_video_urls_to_project("1", self.csv_path)
        except AssertionError:
            raise
        except Exception:
            sa.delete_project("1")

    def test_attach_video_urls_without_name_column(self):
        uploaded, could_not_upload, existing_images = sa.attach_video_urls_to_project(
            self.PROJECT_NAME,
            self.csv_path_without_name_column
        )
        self.assertEqual(len(uploaded), 8)
        self.assertEqual(len(could_not_upload), 0)
        self.assertEqual(len(existing_images), 0)

    def test_get_exports(self):
        sa.attach_video_urls_to_project(
            self.PROJECT_NAME,
            self.csv_path_without_name_column
        )
        sa.prepare_export(self.PROJECT_NAME)
        self.assertEqual(len(sa.get_exports(self.PROJECT_NAME)),1)

    def test_double_attach_image_urls(self):
        uploaded, could_not_upload, existing_images = sa.attach_video_urls_to_project(
            self.PROJECT_NAME,
            os.path.join(dirname(dirname(__file__)), self.PATH_TO_URLS),
        )
        self.assertEqual(len(uploaded), 7)
        self.assertEqual(len(could_not_upload), 0)
        self.assertEqual(len(existing_images), 1)

        uploaded, could_not_upload, existing_images = sa.attach_video_urls_to_project(
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
