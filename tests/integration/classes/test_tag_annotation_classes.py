import tempfile

from src.superannotate import SAClient
sa = SAClient()
from tests.integration.base import BaseTestCase


class TestTagClasses(BaseTestCase):
    PROJECT_NAME = "sample_project_pixel"
    PROJECT_TYPE = "Vector"
    PROJECT_DESCRIPTION = "Example Project test pixel basic images"
    TEST_FOLDER_PTH = "data_set/sample_project_pixel"
    EXAMPLE_IMAGE_1 = "example_image_1.jpg"

    def test_class_creation_type(self):
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
                                "attributes":[
                                   {
                                      "id":57096,
                                      "group_id":21448,
                                      "project_id":7617,
                                      "name":"no",
                                      "count":0,
                                      "createdAt":"2020-09-29T10:39:39.000Z",
                                      "updatedAt":"2020-09-29T10:39:39.000Z"
                                   },
                                   {
                                      "id":57097,
                                      "group_id":21448,
                                      "project_id":7617,
                                      "name":"yes",
                                      "count":1,
                                      "createdAt":"2020-09-29T10:39:39.000Z",
                                      "updatedAt":"2020-09-29T10:48:18.000Z"
                                   }
                                ]
                             }
                          ]
                       },
                       {
                          "id":56821,
                          "project_id":7617,
                          "name":"Large vehicle",
                          "color":"#2ba36d",
                          "count":1,
                          "createdAt":"2020-09-29T10:39:39.000Z",
                          "updatedAt":"2020-09-29T10:48:18.000Z",
                          "attribute_groups":[
                             {
                                "id":21449,
                                "class_id":56821,
                                "name":"small",
                                "is_multiselect":0,
                                "createdAt":"2020-09-29T10:39:39.000Z",
                                "updatedAt":"2020-09-29T10:39:39.000Z",
                                "attributes":[
                                   {
                                      "id":57098,
                                      "group_id":21449,
                                      "project_id":7617,
                                      "name":"yes",
                                      "count":0,
                                      "createdAt":"2020-09-29T10:39:39.000Z",
                                      "updatedAt":"2020-09-29T10:39:39.000Z"
                                   },
                                   {
                                      "id":57099,
                                      "group_id":21449,
                                      "project_id":7617,
                                      "name":"no",
                                      "count":1,
                                      "createdAt":"2020-09-29T10:39:39.000Z",
                                      "updatedAt":"2020-09-29T10:48:18.000Z"
                                   }
                                ]
                             }
                          ]
                       },
                       {
                          "id":56822,
                          "project_id":7617,
                          "name":"Pedestrian",
                          "color":"#d4da03",
                          "count":3,
                          "createdAt":"2020-09-29T10:39:39.000Z",
                          "updatedAt":"2020-09-29T10:48:18.000Z",
                          "attribute_groups":[
    
                          ]
                       },
                       {
                          "id":56823,
                          "project_id":7617,
                          "name":"Two wheeled vehicle",
                          "color":"#f11aec",
                          "count":1,
                          "createdAt":"2020-09-29T10:39:39.000Z",
                          "updatedAt":"2020-09-29T10:48:18.000Z",
                          "attribute_groups":[
    
                          ]
                       },
                       {
                          "id":56824,
                          "project_id":7617,
                          "name":"Traffic sign",
                          "color":"#d8a7fd",
                          "count":9,
                          "createdAt":"2020-09-29T10:39:39.000Z",
                          "updatedAt":"2020-09-29T10:48:18.000Z",
                          "attribute_groups":[
    
                          ]
                       }
                    ]
    
                    '''
                )

            created = sa.create_annotation_classes_from_classes_json(
                self.PROJECT_NAME, temp_path
            )
            self.assertEqual(set([i["type"] for i in created]), {"tag", "object"})