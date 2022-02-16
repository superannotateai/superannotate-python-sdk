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


class TestCreateAnnotationClassNonVectorWithError(BaseTestCase):
    PROJECT_NAME = "test_create_annotation_class"
    PROJECT_TYPE = "Video"
    PROJECT_DESCRIPTION = "Example Project test pixel basic images"

    def test_create_annotation_class(self):
        msg = ""
        try:
            sa.create_annotation_class(self.PROJECT_NAME, "test_add", "#FF0000", type="tag")
        except Exception as e:
            msg = str(e)
        self.assertEqual(msg, "Predefined tagging functionality is not supported for projects of type Video.")


class TestCreateAnnotationClassesNonVectorWithError(BaseTestCase):
    PROJECT_NAME = "test_create_annotation_class"
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

