import os
import tempfile

import pytest
from src.superannotate import AppException
from src.superannotate import SAClient
from src.superannotate.lib.core.entities.classes import AnnotationClassEntity
from tests import DATA_SET_PATH
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestVectorAnnotationClasses(BaseTestCase):
    PROJECT_NAME = "TestVectorAnnotationClasses"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"

    def test_create_annotation_class_search(self):
        sa.create_annotation_class(self.PROJECT_NAME, "tt", "#FFFFFF")
        classes = sa.search_annotation_classes(self.PROJECT_NAME)
        self.assertEqual(len(classes), 1)
        self.assertEqual(classes[0]["type"], "object")
        self.assertEqual(classes[0]["color"], "#FFFFFF")
        sa.create_annotation_class(self.PROJECT_NAME, "tb", "#FFFFFF")
        #  test search
        classes = sa.search_annotation_classes(self.PROJECT_NAME, "bb")
        self.assertEqual(len(classes), 0)
        classes = sa.search_annotation_classes(self.PROJECT_NAME, "tt")
        self.assertEqual(len(classes), 1)

    def test_create_tag_annotation_class(self):
        sa.create_annotation_class(
            self.PROJECT_NAME, "test_add", "#FF0000", class_type="tag"
        )
        classes = sa.search_annotation_classes(self.PROJECT_NAME)
        self.assertEqual(classes[0]["type"], "tag")

    def test_create_annotation_class_with_attr_and_default_value(self):
        _class = sa.create_annotation_class(
            self.PROJECT_NAME,
            "test_add",
            "#FF0000",
            attribute_groups=[
                {
                    "name": "test",
                    "isRequired:": False,
                    "attributes": [{"name": "Car"}, {"name": "Track"}, {"name": "Bus"}],
                    "default_value": "Bus",
                }
            ],
        )
        classes = sa.search_annotation_classes(self.PROJECT_NAME)
        assert classes[0]["attribute_groups"][0]["default_value"] == "Bus"

    @pytest.mark.flaky(reruns=2)
    def test_multi_select_to_checklist(self):
        sa.create_annotation_class(
            self.PROJECT_NAME,
            "test_add",
            "#FF0000",
            class_type="tag",
            attribute_groups=[
                {
                    "name": "test",
                    "group_type": "checklist",
                    "attributes": [{"name": "Car"}, {"name": "Track"}, {"name": "Bus"}],
                }
            ],
        )
        classes = sa.search_annotation_classes(self.PROJECT_NAME)
        assert classes[0]["attribute_groups"][0]["group_type"] == "checklist"
        assert classes[0]["attribute_groups"][0]["default_value"] == []

    @pytest.mark.skip(reason="Need to adjust")
    def test_create_annotation_class_video_error(self):
        msg = ""
        try:
            sa.create_annotation_class(
                self.PROJECT_NAME, "test_add", "#FF0000", class_type="tag"
            )
        except Exception as e:
            msg = str(e)
        self.assertEqual(
            msg,
            "Predefined tagging functionality is not supported for projects of type Video.",
        )

    def test_create_radio_annotation_class_attr_required(self):
        msg = ""
        try:
            sa.create_annotation_class(
                self.PROJECT_NAME,
                "test_add",
                "#FF0000",
                attribute_groups=[
                    {
                        "group_type": "radio",
                        "name": "name",
                    }
                ],
            )
        except Exception as e:
            msg = str(e)
        self.assertEqual(msg, '"classes[0].attribute_groups[0].attributes" is required')

    def test_create_annotation_class_backend_errors(self):

        response = sa.controller.annotation_classes.create(
            sa.controller.projects.get_by_name(self.PROJECT_NAME).data,
            AnnotationClassEntity(
                name="t",
                color="blue",
                attribute_groups=[
                    {"name": "t"},
                    {"name": "t"},
                    {
                        "name": "t",
                        "group_type": "radio",
                        "default_value": [],
                        "attributes": [],
                    },
                ],
            ),
        )

        assert (
            response.errors
            == '"classes[0].attribute_groups[0].attributes" is required.\n'
            '"classes[0].attribute_groups[1].attributes" is required.\n'
            '"classes[0].attribute_groups[2].default_value" must be a string'
        )

    def test_create_annotation_classes_with_empty_default_attribute(self):
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME,
            classes_json=[
                {
                    "name": "Personal vehicle",
                    "color": "#ecb65f",
                    "createdAt": "2020-10-12T11:35:20.000Z",
                    "updatedAt": "2020-10-12T11:48:19.000Z",
                    "attribute_groups": [
                        {
                            "name": "test",
                            "group_type": "radio",
                            "attributes": [
                                {"name": "Car"},
                                {"name": "Track"},
                                {"name": "Bus"},
                            ],
                        }
                    ],
                }
            ],
        )
        classes = sa.search_annotation_classes(self.PROJECT_NAME)
        assert classes[0]["attribute_groups"][0]["default_value"] is None

    def test_class_creation_type(self):
        with tempfile.TemporaryDirectory() as tmpdir_name:
            temp_path = f"{tmpdir_name}/new_classes.json"
            with open(temp_path, "w") as new_classes:
                new_classes.write(
                    """
                    [
                       {
                          "id":56820,
                          "project_id":7617,
                          "name":"Personal vehicle",
                          "color":"#547497",
                          "createdAt":"2020-09-29T10:39:39.000Z",
                          "updatedAt":"2020-09-29T10:48:18.000Z",
                          "type": "tag",
                          "attribute_groups":[
                             {
                                "id":21448,
                                "class_id":56820,
                                "name":"Large",
                                "createdAt":"2020-09-29T10:39:39.000Z",
                                "updatedAt":"2020-09-29T10:39:39.000Z",
                                "attributes":[
                                   {
                                      "id":57096,
                                      "group_id":21448,
                                      "project_id":7617,
                                      "name":"no",
                                      "createdAt":"2020-09-29T10:39:39.000Z",
                                      "updatedAt":"2020-09-29T10:39:39.000Z"
                                   },
                                   {
                                      "id":57097,
                                      "group_id":21448,
                                      "project_id":7617,
                                      "name":"yes",
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
                          "createdAt":"2020-09-29T10:39:39.000Z",
                          "updatedAt":"2020-09-29T10:48:18.000Z",
                          "attribute_groups":[
                             {
                                "id":21449,
                                "class_id":56821,
                                "name":"small",
                                "createdAt":"2020-09-29T10:39:39.000Z",
                                "updatedAt":"2020-09-29T10:39:39.000Z",
                                "attributes":[
                                   {
                                      "id":57098,
                                      "group_id":21449,
                                      "project_id":7617,
                                      "name":"yes",
                                      "createdAt":"2020-09-29T10:39:39.000Z",
                                      "updatedAt":"2020-09-29T10:39:39.000Z"
                                   },
                                   {
                                      "id":57099,
                                      "group_id":21449,
                                      "project_id":7617,
                                      "name":"no",
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
                          "createdAt":"2020-09-29T10:39:39.000Z",
                          "updatedAt":"2020-09-29T10:48:18.000Z",
                          "attribute_groups":[

                          ]
                       }
                    ]

                    """
                )

            created = sa.create_annotation_classes_from_classes_json(
                self.PROJECT_NAME, temp_path
            )
            self.assertEqual({i["type"] for i in created}, {"tag", "object"})


class TestVideoCreateAnnotationClasses(BaseTestCase):
    PROJECT_NAME = "TestVideoCreateAnnotationClasses"
    PROJECT_TYPE = "Video"
    PROJECT_DESCRIPTION = "Example Project test pixel basic images"

    @pytest.mark.skip(reason="Need to adjust")
    def test_create_annotation_class(self):
        with tempfile.TemporaryDirectory() as tmpdir_name:
            temp_path = f"{tmpdir_name}/new_classes.json"
            with open(temp_path, "w") as new_classes:
                new_classes.write(
                    """
                    [
                       {
                          "id":56820,
                          "project_id":7617,
                          "name":"Personal vehicle",
                          "color":"#547497",
                          "createdAt":"2020-09-29T10:39:39.000Z",
                          "updatedAt":"2020-09-29T10:48:18.000Z",
                          "type": "tag",
                          "attribute_groups":[
                             {
                                "id":21448,
                                "class_id":56820,
                                "name":"Large",
                                "createdAt":"2020-09-29T10:39:39.000Z",
                                "updatedAt":"2020-09-29T10:39:39.000Z",
                                "attributes":[]
                             }
                          ]
                       }
                    ]

                    """
                )
            msg = ""
            try:
                sa.create_annotation_classes_from_classes_json(
                    self.PROJECT_NAME, temp_path
                )
            except Exception as e:
                msg = str(e)
            self.assertEqual(
                msg,
                "Predefined tagging functionality is not supported for projects of type Video.",
            )

    def test_create_annotation_class_via_ocr_group_type(self):
        with self.assertRaisesRegexp(
            AppException,
            f"OCR attribute group is not supported for project type {self.PROJECT_TYPE}.",
        ):
            attribute_groups = [
                {
                    "id": 21448,
                    "class_id": 56820,
                    "name": "Large",
                    "group_type": "ocr",
                    "createdAt": "2020-09-29T10:39:39.000Z",
                    "updatedAt": "2020-09-29T10:39:39.000Z",
                    "attributes": [],
                }
            ]
            sa.create_annotation_class(
                self.PROJECT_NAME,
                "test_add",
                "#FF0000",
                attribute_groups,  # noqa
                class_type="tag",
            )


class TestPixelCreateAnnotationClass(BaseTestCase):
    PROJECT_NAME = "TestCreateAnnotationClassPixel"
    PROJECT_TYPE = "Pixel"
    PROJECT_DESCRIPTION = "Example "
    TEST_LARGE_CLASSES_JSON = "large_classes_json.json"

    @property
    def large_json_path(self):
        return os.path.join(DATA_SET_PATH, self.TEST_LARGE_CLASSES_JSON)

    def test_create_annotation_class_with_default_attribute(self):
        with self.assertRaisesRegexp(
            AppException,
            'The "default_value" key is not supported for project type Pixel.',
        ):
            sa.create_annotation_class(
                self.PROJECT_NAME,
                "test_add",
                "#FF0000",
                attribute_groups=[
                    {
                        "name": "test",
                        "attributes": [
                            {"name": "Car"},
                            {"name": "Track"},
                            {"name": "Bus"},
                        ],
                        "default_value": "Bus",
                    }
                ],
            )


class TestDocumentAnnotationClasses(BaseTestCase):
    PROJECT_NAME = "TestDocumentAnnotationClasses"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Document"

    def test_document_project_create_annotation_class_search(self):
        sa.create_annotation_class(
            self.PROJECT_NAME, name="tt", color="#FFFFFF", class_type="relationship"
        )
        classes = sa.search_annotation_classes(self.PROJECT_NAME)
        self.assertEqual(len(classes), 1)
        self.assertEqual(classes[0]["type"], "relationship")
        self.assertEqual(classes[0]["color"], "#FFFFFF")
        sa.create_annotation_class(self.PROJECT_NAME, name="tb", color="#FFFFFF")
        #  test search
        classes = sa.search_annotation_classes(self.PROJECT_NAME, "bb")
        self.assertEqual(len(classes), 0)
        classes = sa.search_annotation_classes(self.PROJECT_NAME, "tt")
        self.assertEqual(len(classes), 1)
