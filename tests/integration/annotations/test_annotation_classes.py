from urllib.parse import urlparse
import os
from pathlib import Path
from src.superannotate import SAClient
sa = SAClient()
from tests.integration.base import BaseTestCase


class TestAnnotationClasses(BaseTestCase):
    PROJECT_NAME_ = "TestAnnotationClasses"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"
    CLASSES_JON_PATH = "data_set/invalid_json/classes.json"

    @property
    def classes_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.CLASSES_JON_PATH)

    def test_invalid_json(self):
        try:
            sa.create_annotation_classes_from_classes_json(self.PROJECT_NAME, self.classes_path)
        except Exception as e:
            self.assertIn("Couldn't validate annotation classes", str(e))

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
