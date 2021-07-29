import time

import src.lib.app.superannotate as sa
from src.tests.integration.base import BaseTestCase


class TestAnnotationClasses(BaseTestCase):
    PROJECT_NAME_ = "TestAnnotationClasses"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"

    def test_annotation_classes(self):
        annotation_classes = sa.search_annotation_classes(self.PROJECT_NAME)
        self.assertEqual(len(annotation_classes), 0)
        sa.create_annotation_class(self.PROJECT_NAME, "fff", "#FFFFFF")
        time.sleep(1)
        annotation_classes = sa.search_annotation_classes(self.PROJECT_NAME)
        self.assertEqual(len(annotation_classes), 1)

        annotation_class = sa.search_annotation_classes(self.PROJECT_NAME, "ff")[0]
        time.sleep(1)
        sa.delete_annotation_class(self.PROJECT_NAME, annotation_class)
        time.sleep(1)
        annotation_classes = sa.search_annotation_classes(self.PROJECT_NAME)
        self.assertEqual(len(annotation_classes), 0)
