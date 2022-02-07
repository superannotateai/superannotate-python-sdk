import tempfile

import src.superannotate as sa
from tests.integration.base import BaseTestCase


class TestCreateAnnotationClass(BaseTestCase):
    PROJECT_NAME = "test_create_annotation_class"
    PROJECT_TYPE = "Vector"
    PROJECT_DESCRIPTION = "Example Project test pixel basic images"
    TEST_FOLDER_PTH = "data_set/sample_project_pixel"
    EXAMPLE_IMAGE_1 = "example_image_1.jpg"

    def test_create_annotation_class(self):
        sa.create_annotation_class(self.PROJECT_NAME, "test_add", "#FF0000", type="tag")
        classes = sa.search_annotation_classes(self.PROJECT_NAME)
        self.assertEqual(classes[0]["type"], "tag")
