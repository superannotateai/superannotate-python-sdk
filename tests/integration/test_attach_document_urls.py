import os
from os.path import dirname
from os.path import join

from src.superannotate import SAClient
sa = SAClient()
from src.superannotate import AppException
import src.superannotate.lib.core as constances
from tests.integration.base import BaseTestCase


class TestDocumentUrls(BaseTestCase):
    PROJECT_NAME = "document attach urls"
    PATH_TO_URLS = "csv_files/text_urls.csv"
    PATH_TO_50K_URLS = "501_urls.csv"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Document"
