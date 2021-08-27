from urllib.parse import urlparse

import src.superannotate as sa
from tests.integration.base import BaseTestCase


class TestAnnotationClasses(BaseTestCase):
    PROJECT_NAME_ = "TestAnnotationClasses"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"

    def test_annotation_classes(self):
        annotation_classes = sa.search_annotation_classes(self.PROJECT_NAME)
        self.assertEqual(len(annotation_classes), 0)
        sa.create_annotation_class(self.PROJECT_NAME, "fff", "#FFFFFF")
        annotation_classes = sa.search_annotation_classes(self.PROJECT_NAME)
        self.assertEqual(len(annotation_classes), 1)

        annotation_class = sa.search_annotation_classes(self.PROJECT_NAME, "ff")[0]
        sa.delete_annotation_class(self.PROJECT_NAME, annotation_class)
        annotation_classes = sa.search_annotation_classes(self.PROJECT_NAME)
        self.assertEqual(len(annotation_classes), 0)

    def test_annotation_classes_from_s3(self):
        annotation_classes = sa.search_annotation_classes(self.PROJECT_NAME)
        self.assertEqual(len(annotation_classes), 0)
        f = urlparse("s3://superannotate-python-sdk-test/sample_project_pixel")

        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME,
            f.path[1:] + "/classes/classes.json",
            from_s3_bucket=f.netloc,
        )
        annotation_classes = sa.search_annotation_classes(self.PROJECT_NAME)
        self.assertEqual(len(annotation_classes), 5)
