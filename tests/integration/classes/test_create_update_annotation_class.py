import tempfile
from copy import deepcopy

import pytest
from src.superannotate import AppException
from src.superannotate import SAClient
from src.superannotate.lib.core.entities.classes import AnnotationClassEntity
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
        tt_class_id = classes[0]["id"]
        self.assertEqual(classes[0]["type"], "object")
        self.assertEqual(classes[0]["color"], "#FFFFFF")
        sa.create_annotation_class(self.PROJECT_NAME, "tb", "#FFFFFF")
        #  test search
        classes = sa.search_annotation_classes(self.PROJECT_NAME, "bb")
        self.assertEqual(len(classes), 0)
        classes = sa.search_annotation_classes(self.PROJECT_NAME, "tt")
        self.assertEqual(len(classes), 1)

        res_1 = sa.get_annotation_class(self.PROJECT_NAME, "tt")
        res_2 = sa.get_annotation_class(self.PROJECT_NAME, tt_class_id)
        assert res_1["name"] == res_2["name"]
        assert res_1["id"] == res_2["id"]
        assert res_1["type"] == res_2["type"]

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
            == '"classes[0].attribute_groups[0].attributes" is required\n'
            '"classes[0].attribute_groups[1].attributes" is required\n'
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

    def test_update_annotation_class_attribute_groups(self):
        # Create initial annotation class with attribute groups
        sa.create_annotation_class(
            self.PROJECT_NAME,
            "test_update",
            "#FF0000",
            attribute_groups=[
                {
                    "name": "Size",
                    "group_type": "radio",
                    "attributes": [{"name": "Small"}, {"name": "Large"}],
                    "default_value": "Small",
                    "isRequired": False,
                }
            ],
            class_type="object",
        )

        # Retrieve the created class
        classes = sa.search_annotation_classes(self.PROJECT_NAME, "test_update")
        self.assertEqual(len(classes), 1)
        existing_class = classes[0]

        # Verify initial state
        self.assertEqual(len(existing_class["attribute_groups"]), 1)
        self.assertEqual(len(existing_class["attribute_groups"][0]["attributes"]), 2)

        # Modify attribute groups - add new attribute to existing group
        updated_groups = existing_class["attribute_groups"]
        updated_groups[0]["isRequired"] = True
        updated_groups[0]["attributes"].append({"name": "Medium"})

        # Add a new attribute group
        updated_groups.append(
            {
                "group_type": "checklist",
                "name": "Color",
                "attributes": [{"name": "Red"}, {"name": "Blue"}, {"name": "Green"}],
            }
        )

        # Update the annotation class
        update_response = sa.update_annotation_class(
            self.PROJECT_NAME, "test_update", attribute_groups=updated_groups
        )

        # Verify updates
        classes = sa.search_annotation_classes(self.PROJECT_NAME, "test_update")
        # Verify response matches the current class state
        self.assertEqual(update_response["id"], classes[0]["id"])
        self.assertEqual(update_response["name"], classes[0]["name"])
        self.assertEqual(update_response["color"], classes[0]["color"])
        self.assertEqual(update_response["type"], classes[0]["type"])
        self.assertEqual(
            len(update_response["attribute_groups"]),
            len(classes[0]["attribute_groups"]),
        )

        # Verify each attribute group matches
        for resp_group, class_group in zip(
            update_response["attribute_groups"], classes[0]["attribute_groups"]
        ):
            self.assertEqual(resp_group["name"], class_group["name"])
            self.assertEqual(resp_group["group_type"], class_group["group_type"])
            self.assertEqual(resp_group["isRequired"], class_group["isRequired"])
            self.assertEqual(
                len(resp_group["attributes"]), len(class_group["attributes"])
            )

            # Verify each attribute matches
            for resp_attr, class_attr in zip(
                resp_group["attributes"], class_group["attributes"]
            ):
                self.assertEqual(resp_attr["name"], class_attr["name"])
        self.assertEqual(len(classes), 1)
        updated_class = classes[0]

        # Check that we now have 2 attribute groups
        self.assertEqual(len(updated_class["attribute_groups"]), 2)

        # Check first group has 3 attributes now
        size_group = next(
            g for g in updated_class["attribute_groups"] if g["name"] == "Size"
        )
        self.assertEqual(len(size_group["attributes"]), 3)
        attribute_names = [attr["name"] for attr in size_group["attributes"]]
        self.assertIn("Medium", attribute_names)
        # Verify isRequired was updated
        self.assertTrue(size_group["isRequired"])

        # Check second group exists with correct attributes
        color_group = next(
            g for g in updated_class["attribute_groups"] if g["name"] == "Color"
        )
        self.assertEqual(color_group["group_type"], "checklist")
        self.assertEqual(len(color_group["attributes"]), 3)

    def test_update_annotation_class_rename_attributes(self):
        # Create annotation class
        sa.create_annotation_class(
            self.PROJECT_NAME,
            "test_update_rename",
            "#00FF00",
            attribute_groups=[
                {
                    "name": "Quality",
                    "group_type": "radio",
                    "attributes": [{"name": "Good"}, {"name": "Bad"}],
                }
            ],
        )

        # Retrieve and rename attribute
        classes = sa.search_annotation_classes(self.PROJECT_NAME, "test_update_rename")
        updated_groups = classes[0]["attribute_groups"]
        updated_groups[0]["attributes"][0]["name"] = "Excellent"
        updated_groups[0]["name"] = "Rating"

        # Update
        sa.update_annotation_class(
            self.PROJECT_NAME, "test_update_rename", attribute_groups=updated_groups
        )

        # Verify
        classes = sa.search_annotation_classes(self.PROJECT_NAME, "test_update_rename")
        rating_group = classes[0]["attribute_groups"][0]
        self.assertEqual(rating_group["name"], "Rating")
        self.assertEqual(rating_group["attributes"][0]["name"], "Excellent")

    def test_update_annotation_class_delete_attributes(self):
        # Create annotation class with multiple attributes
        sa.create_annotation_class(
            self.PROJECT_NAME,
            "test_update_delete",
            "#0000FF",
            attribute_groups=[
                {
                    "name": "Status",
                    "group_type": "checklist",
                    "attributes": [
                        {"name": "Active"},
                        {"name": "Inactive"},
                        {"name": "Pending"},
                    ],
                }
            ],
        )

        # Retrieve and remove one attribute
        classes = sa.search_annotation_classes(self.PROJECT_NAME, "test_update_delete")
        updated_groups = classes[0]["attribute_groups"]
        updated_groups[0]["attributes"] = [
            attr
            for attr in updated_groups[0]["attributes"]
            if attr["name"] != "Pending"
        ]

        # Update
        sa.update_annotation_class(
            self.PROJECT_NAME, "test_update_delete", attribute_groups=updated_groups
        )

        # Verify
        classes = sa.search_annotation_classes(self.PROJECT_NAME, "test_update_delete")
        status_group = classes[0]["attribute_groups"][0]
        self.assertEqual(len(status_group["attributes"]), 2)
        attribute_names = [attr["name"] for attr in status_group["attributes"]]
        self.assertNotIn("Pending", attribute_names)

    def test_update_annotation_class_change_required_and_default(self):
        # Create annotation class
        sa.create_annotation_class(
            self.PROJECT_NAME,
            "test_update_required",
            "#FFFF00",
            attribute_groups=[
                {
                    "name": "Priority",
                    "group_type": "radio",
                    "attributes": [
                        {"name": "Low"},
                        {"name": "Medium"},
                        {"name": "High"},
                    ],
                    "default_value": "Low",
                    "isRequired": False,
                }
            ],
        )

        # Retrieve and update required state and default value
        classes = sa.search_annotation_classes(
            self.PROJECT_NAME, "test_update_required"
        )
        updated_groups = classes[0]["attribute_groups"]
        updated_groups[0]["isRequired"] = True
        updated_groups[0]["attributes"][0]["default"] = 0
        updated_groups[0]["attributes"][1]["default"] = 1

        # Update
        sa.update_annotation_class(
            self.PROJECT_NAME, "test_update_required", attribute_groups=updated_groups
        )

        # Verify
        classes = sa.search_annotation_classes(
            self.PROJECT_NAME, "test_update_required"
        )
        priority_group = classes[0]["attribute_groups"][0]
        self.assertTrue(priority_group["isRequired"])
        self.assertEqual(priority_group["default_value"], "Medium")

    def test_update_annotation_class_change_group_type(self):
        # Create annotation class
        sa.create_annotation_class(
            self.PROJECT_NAME,
            "test_update_type",
            "#FF00FF",
            attribute_groups=[
                {
                    "name": "Options",
                    "group_type": "radio",
                    "attributes": [{"name": "Option1"}, {"name": "Option2"}],
                }
            ],
        )

        # Retrieve and change group type
        classes = sa.search_annotation_classes(self.PROJECT_NAME, "test_update_type")
        updated_groups = classes[0]["attribute_groups"]
        updated_groups[0]["group_type"] = "checklist"

        # Update
        sa.update_annotation_class(
            self.PROJECT_NAME, "test_update_type", attribute_groups=updated_groups
        )

        # Verify
        classes = sa.search_annotation_classes(self.PROJECT_NAME, "test_update_type")
        options_group = classes[0]["attribute_groups"][0]
        self.assertEqual(options_group["group_type"], "checklist")

    def test_update_annotation_class_no_changes(self):
        # Create annotation class
        sa.create_annotation_class(
            self.PROJECT_NAME,
            "test_update_nochange",
            "#00FFFF",
            attribute_groups=[
                {
                    "name": "Category",
                    "group_type": "radio",
                    "attributes": [{"name": "A"}, {"name": "B"}],
                }
            ],
        )

        # Retrieve class
        classes = sa.search_annotation_classes(
            self.PROJECT_NAME, "test_update_nochange"
        )

        # Update with same data
        update_response = sa.update_annotation_class(
            self.PROJECT_NAME,
            "test_update_nochange",
            attribute_groups=classes[0]["attribute_groups"],
        )

        # Verify response matches the current class state
        self.assertEqual(update_response["id"], classes[0]["id"])
        self.assertEqual(update_response["name"], classes[0]["name"])
        self.assertEqual(update_response["color"], classes[0]["color"])
        self.assertEqual(update_response["type"], classes[0]["type"])
        self.assertEqual(
            len(update_response["attribute_groups"]),
            len(classes[0]["attribute_groups"]),
        )

    def test_update_annotation_class_duplicated_groups(self):
        # Create annotation class
        sa.create_annotation_class(
            self.PROJECT_NAME,
            "test_update_nochange",
            "#00FFFF",
            attribute_groups=[
                {
                    "name": "Category",
                    "group_type": "radio",
                    "attributes": [{"name": "A"}, {"name": "B"}],
                }
            ],
        )

        # Retrieve class
        classes = sa.search_annotation_classes(
            self.PROJECT_NAME, "test_update_nochange"
        )

        # Update with same data
        new_group = deepcopy(classes[0]["attribute_groups"][0])
        new_group["name"] = "New name"
        new_group["attributes"][0]["name"] = "New attr1"
        new_group["attributes"][1]["name"] = "New attr2"
        update_response = sa.update_annotation_class(
            self.PROJECT_NAME,
            "test_update_nochange",
            attribute_groups=[classes[0]["attribute_groups"][0], new_group],
        )
        # not validated response, second class that contain ids ignored
        assert len(update_response["attribute_groups"]) == 1
        assert True

    def test_update_annotation_class_invalid_group_type(self):
        # Create annotation class
        sa.create_annotation_class(
            self.PROJECT_NAME,
            "test_update_nochange",
            "#00FFFF",
            attribute_groups=[
                {
                    "name": "Category",
                    "group_type": "radio",
                    "attributes": [{"name": "A"}, {"name": "B"}],
                }
            ],
        )

        # Retrieve class
        classes = sa.search_annotation_classes(
            self.PROJECT_NAME, "test_update_nochange"
        )

        classes[0]["attribute_groups"][0]["group_type"] = "invalid"
        with self.assertRaisesRegexp(AppException, "Invalid group_type: invalid"):
            sa.update_annotation_class(
                self.PROJECT_NAME,
                "test_update_nochange",
                attribute_groups=classes[0]["attribute_groups"],
            )

    def test_update_annotation_class_without_group_type(self):
        # Create annotation class
        sa.create_annotation_class(
            self.PROJECT_NAME,
            "test_update_nochange",
            "#00FFFF",
            attribute_groups=[
                {
                    "name": "Category",
                    "group_type": "radio",
                    "attributes": [{"name": "A"}, {"name": "B"}],
                }
            ],
        )

        # Retrieve class
        classes = sa.search_annotation_classes(
            self.PROJECT_NAME, "test_update_nochange"
        )

        del classes[0]["attribute_groups"][0]["group_type"]
        with self.assertRaisesRegexp(AppException, "Invalid group_type: invalid"):
            res = sa.update_annotation_class(
                self.PROJECT_NAME,
                "test_update_nochange",
                attribute_groups=classes[0]["attribute_groups"],
            )
            assert res["attribute_groups"][0]["group_type"] == "radio"


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
