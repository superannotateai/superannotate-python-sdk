from src.superannotate import SAClient
from tests.integration.base import BaseTestCase


sa = SAClient()


class TestVectorAnnotationClassesDelete(BaseTestCase):
    PROJECT_NAME = "TestVectorAnnotationClassesDelete"
    PROJECT_DESCRIPTION = "test description"
    PROJECT_TYPE = "Vector"

    def setUp(self, *args, **kwargs):
        super().setUp()
        sa.create_annotation_class(
            self.PROJECT_NAME, "test_annotation_class", "#FFFFFF"
        )
        classes = sa.search_annotation_classes(self.PROJECT_NAME)
        self.assertEqual(len(classes), 1)

    def test_delete_annotation_class(self):
        sa.delete_annotation_class(self.PROJECT_NAME, "test_annotation_class")
        classes = sa.search_annotation_classes(self.PROJECT_NAME)
        self.assertEqual(len(classes), 0)
