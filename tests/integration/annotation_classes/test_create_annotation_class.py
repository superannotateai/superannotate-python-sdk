import os
from pathlib import Path

from src.superannotate import SAClient
sa = SAClient()
from tests.integration.base import BaseTestCase


class TestDocumentCreateAnnotationClass(BaseTestCase):
    PROJECT_NAME = "TestDocumentCreateAnnotationClass"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Document"

    def test_create_annotation_class(self):
        sa.create_annotation_class(
            self.PROJECT_NAME,
            "test_add",
            "#FF0000",
            [{"name": "height", "attributes": [{"name": "tall"}, {"name": "short"}]}],
            class_type="tag"
        )

        self.assertEqual(len(sa.search_annotation_classes(self.PROJECT_NAME)), 1)
