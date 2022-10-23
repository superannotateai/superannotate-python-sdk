from src.superannotate import SAClient
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestCreateAnnotationClass(BaseTestCase):
    PROJECT_NAME = "TestCreateAnnotationClassBED"
    PROJECT_TYPE = "Vector"
    PROJECT_DESCRIPTION = "Example "
    TEST_LARGE_CLASSES_JSON = "large_classes_json.json"
    EXAMPLE_IMAGE_1 = "example_image_1.jpg"

    def test_multi_select_to_checklist(self):
        sa.create_annotation_class(
            self.PROJECT_NAME,
            "test_add",
            "#FF0000",
            class_type="tag",
            attribute_groups=[
                {
                    "name": "test",
                    "is_multiselect": 1,
                    "attributes": [{"name": "Car"}, {"name": "Track"}, {"name": "Bus"}],

                }
            ]
        )
        classes = sa.search_annotation_classes(self.PROJECT_NAME)
        assert classes[0]["attribute_groups"][0]["group_type"] == 'checklist'
        assert classes[0]["attribute_groups"][0]["default_value"] == []


