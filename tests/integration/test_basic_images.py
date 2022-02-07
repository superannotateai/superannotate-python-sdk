import json
import os
import tempfile
from os.path import dirname
from pathlib import Path

import src.superannotate as sa
from tests.integration.base import BaseTestCase


class TestPixelImages(BaseTestCase):
    PROJECT_NAME = "sample_project_pixel"
    PROJECT_TYPE = "Pixel"
    PROJECT_DESCRIPTION = "Example Project test pixel basic images"
    TEST_FOLDER_PTH = "data_set/sample_project_pixel"
    EXAMPLE_IMAGE_1 = "example_image_1.jpg"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PTH)

    @property
    def classes_json_path(self):
        return f"{self.folder_path}/classes/classes.json"

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


            sa.create_annotation_classes_from_classes_json(
                self.PROJECT_NAME, temp_path
            )

    def test_basic_images(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            sa.upload_images_from_folder_to_project(
                self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
            )
            sa.create_annotation_classes_from_classes_json(
                self.PROJECT_NAME, self.classes_json_path
            )
            image = sa.get_image_metadata(self.PROJECT_NAME,image_name="example_image_1.jpg" )
            image['createdAt'] = ''
            image['updatedAt'] = ''
            truth ={'name': 'example_image_1.jpg', 'path': None, 'annotation_status': 'InProgress', 'prediction_status':'NotStarted', 'segmentation_status': 'NotStarted', 'approval_status': None, 'is_pinned': 0, 'annotator_name': None, 'qa_name': None, 'entropy_value': None, 'createdAt': '', 'updatedAt': ''}

            self.assertEqual(image,truth)

            sa.upload_image_annotations(
                project=self.PROJECT_NAME,
                image_name=self.EXAMPLE_IMAGE_1,
                annotation_json=f"{self.folder_path}/{self.EXAMPLE_IMAGE_1}___pixel.json",
            )
            downloaded = sa.download_image(
                project=self.PROJECT_NAME,
                image_name=self.EXAMPLE_IMAGE_1,
                local_dir_path=temp_dir,
                include_annotations=True,
            )
            self.assertNotEqual(downloaded[1], (None, None))
            self.assertGreater(len(downloaded[0]), 0)

            sa.download_image_annotations(
                self.PROJECT_NAME, self.EXAMPLE_IMAGE_1, temp_dir
            )
            self.assertEqual(len(list(Path(temp_dir).glob("*"))), 3)


class TestVectorImages(BaseTestCase):
    PROJECT_NAME = "sample_project_vector"
    PROJECT_TYPE = "Vector"
    PROJECT_DESCRIPTION = "Example Project test vector basic images"
    TEST_FOLDER_PTH = "data_set/sample_project_vector"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PTH)

    @folder_path.setter
    def folder_path(self, value):
        self._folder_path = value

    @property
    def classes_json_path(self):
        return f"{self.folder_path}/classes/classes.json"

    def test_basic_images(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            sa.upload_images_from_folder_to_project(
                self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
            )
            sa.create_annotation_classes_from_classes_json(
                self.PROJECT_NAME, self.classes_json_path
            )
            images = sa.search_images(self.PROJECT_NAME, "example_image_1")
            self.assertEqual(len(images), 1)

            image_name = images[0]

            image = sa.get_image_metadata(self.PROJECT_NAME,image_name="example_image_1.jpg" )
            image['createdAt'] = ''
            image['updatedAt'] = ''
            truth = {'name': 'example_image_1.jpg', 'path': None, 'annotation_status': 'InProgress', 'prediction_status':'NotStarted', 'segmentation_status': None, 'approval_status': None, 'is_pinned': 0, 'annotator_name': None, 'qa_name': None, 'entropy_value': None, 'createdAt': '', 'updatedAt': ''}
            self.assertEqual(image, truth)

            sa.download_image(self.PROJECT_NAME, image_name, temp_dir, True)
            self.assertEqual(
                sa.get_image_annotations(self.PROJECT_NAME, image_name)[
                    "annotation_json"
                ],
                None,
            )