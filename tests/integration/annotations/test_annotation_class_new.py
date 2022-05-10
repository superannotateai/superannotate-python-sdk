import os
from pathlib import Path
from unittest import TestCase

from src.superannotate import SAClient
sa = SAClient()
from tests.integration.base import BaseTestCase


class TestAnnotationClasses(BaseTestCase):
    PROJECT_NAME = "test_annotation_class_new"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"

    @property
    def classes_json(self):
        return os.path.join(Path(__file__).parent.parent.parent,
            "data_set/sample_project_vector/classes/classes.json",
        )

    def test_create_annotation_class(self):
        sa.create_annotation_class(self.PROJECT_NAME, "tt", "#FFFFFF")
        classes = sa.search_annotation_classes(self.PROJECT_NAME)
        self.assertEqual(len(classes), 1)
        self.assertEqual(classes[0]['type'], 'object')

    def test_annotation_classes_filter(self):
        sa.create_annotation_class(self.PROJECT_NAME, "tt", "#FFFFFF")
        sa.create_annotation_class(self.PROJECT_NAME, "tb", "#FFFFFF")
        classes = sa.search_annotation_classes(self.PROJECT_NAME, "bb")
        self.assertEqual(len(classes), 0)
        classes = sa.search_annotation_classes(self.PROJECT_NAME, "tt")
        self.assertEqual(len(classes), 1)

    def test_create_annotation_class_from_json(self):
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.classes_json
        )
        self.assertEqual(len(sa.search_annotation_classes(self.PROJECT_NAME)), 4)

        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.classes_json
        )
        self.assertEqual(len(sa.search_annotation_classes(self.PROJECT_NAME)), 4)
