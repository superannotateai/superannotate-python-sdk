import os
from os.path import dirname
import tempfile

import src.superannotate as sa
from tests.integration.base import BaseTestCase
from tests import DATA_SET_PATH


class TestCreateAnnotationClass(BaseTestCase):
    PROJECT_NAME = "TestCreateAnnotationClass"
    PROJECT_TYPE = "Vector"
    PROJECT_DESCRIPTION = "Example "
    TEST_LARGE_CLASSES_JSON = "large_classes_json.json"
    EXAMPLE_IMAGE_1 = "example_image_1.jpg"

    @property
    def large_json_path(self):
        return os.path.join(DATA_SET_PATH, self.TEST_LARGE_CLASSES_JSON)

    def test_create_annotation_class(self):
        sa.create_annotation_class(self.PROJECT_NAME, "test_add", "#FF0000", class_type="tag")
        classes = sa.search_annotation_classes(self.PROJECT_NAME)
        self.assertEqual(classes[0]["type"], "tag")

    def test_create_annotations_classes_from_class_json(self):
        classes = sa.create_annotation_classes_from_classes_json(self.PROJECT_NAME, self.large_json_path)
        self.assertEqual(len(classes), 1500)

    def test_hex_color_adding(self):
        sa.create_annotation_class(self.PROJECT_NAME, "test_add", color="#0000FF")
        classes = sa.search_annotation_classes(self.PROJECT_NAME, "test_add")
        assert classes[0]["color"] == "#0000FF"


class TestCreateAnnotationClassNonVectorWithError(BaseTestCase):
    PROJECT_NAME = "TestCreateAnnotationClassNonVectorWithError"
    PROJECT_TYPE = "Video"
    PROJECT_DESCRIPTION = "Example Project test pixel basic images"

    def test_create_annotation_class(self):
        msg = ""
        try:
            sa.create_annotation_class(self.PROJECT_NAME, "test_add", "#FF0000", class_type="tag")
        except Exception as e:
            msg = str(e)
        self.assertEqual(msg, "Predefined tagging functionality is not supported for projects of type Video.")


class TestCreateAnnotationClassesNonVectorWithError(BaseTestCase):
    PROJECT_NAME = "TestCreateAnnotationClassesNonVectorWithError"
    PROJECT_TYPE = "Video"
    PROJECT_DESCRIPTION = "Example Project test pixel basic images"

    def test_create_annotation_class(self):
        with tempfile.TemporaryDirectory() as tmpdir_name:
            temp_path = f"{tmpdir_name}/new_classes.json"
            with open(temp_path,
                      "w") as new_classes:
                new_classes.write(
                    '''
                    [
                       {
                          "id":56820,
                          "project_id":7617,
                          "name":"Personal vehicle",
                          "color":"#547497",
                          "count":18,
                          "createdAt":"2020-09-29T10:39:39.000Z",
                          "updatedAt":"2020-09-29T10:48:18.000Z",
                          "type": "tag",
                          "attribute_groups":[
                             {
                                "id":21448,
                                "class_id":56820,
                                "name":"Large",
                                "is_multiselect":0,
                                "createdAt":"2020-09-29T10:39:39.000Z",
                                "updatedAt":"2020-09-29T10:39:39.000Z",
                                "attributes":[]
                             }
                          ]
                       }
                    ]

                    '''
                )
            msg = ""
            try:
                sa.create_annotation_classes_from_classes_json(
                    self.PROJECT_NAME, temp_path
                )
            except Exception as e:
                msg = str(e)
            self.assertEqual(msg, "Predefined tagging functionality is not supported for projects of type Video.")

