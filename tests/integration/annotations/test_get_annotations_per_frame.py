import os
from os.path import dirname
from tests.integration.base import BaseTestCase


class TestGetAnnotations(BaseTestCase):
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

