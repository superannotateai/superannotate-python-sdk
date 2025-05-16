from src.superannotate import AppException
from src.superannotate import SAClient
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestProjectSteps(BaseTestCase):
    PROJECT_NAME = "TestProjectSteps"
    PROJECT_TYPE = "Vector"

    def setUp(self, *args, **kwargs):
        super().setUp()
        sa.create_annotation_class(
            self.PROJECT_NAME,
            "transport",
            "#FF0000",
            attribute_groups=[
                {
                    "name": "transport_group",
                    "attributes": [{"name": "Car"}, {"name": "Track"}, {"name": "Bus"}],
                    "default_value": "Bus",
                }
            ],
        )
        sa.create_annotation_class(
            self.PROJECT_NAME,
            "passenger",
            "#FF1000",
            attribute_groups=[
                {
                    "name": "passenger_group",
                    "attributes": [{"name": "white"}, {"name": "black"}],
                }
            ],
        )
        self._classes = sa.search_annotation_classes(self.PROJECT_NAME)

    def test_create_steps(self):
        sa.set_project_steps(
            self.PROJECT_NAME,
            steps=[
                {
                    "class_id": self._classes[0]["id"],
                    "attribute": [
                        {
                            "attribute": {
                                "id": self._classes[0]["attribute_groups"][0][
                                    "attributes"
                                ][0]["id"],
                                "group_id": self._classes[0]["attribute_groups"][0][
                                    "id"
                                ],
                            }
                        }
                    ],
                },
                {
                    "class_id": self._classes[1]["id"],
                    "attribute": [
                        {
                            "attribute": {
                                "id": self._classes[1]["attribute_groups"][0][
                                    "attributes"
                                ][0]["id"],
                                "group_id": self._classes[1]["attribute_groups"][0][
                                    "id"
                                ],
                            }
                        }
                    ],
                },
            ],
            connections=[[1, 2]],
        )
        steps = sa.get_project_steps(self.PROJECT_NAME)
        assert len(steps) == 2

    def test_missing_ids(self):
        with self.assertRaisesRegexp(AppException, "Annotation class not found."):
            sa.set_project_steps(
                self.PROJECT_NAME,
                steps=[
                    {
                        "class_id": 1,  # invalid class id
                        "attribute": [
                            {
                                "attribute": {
                                    "id": self._classes[0]["attribute_groups"][0][
                                        "attributes"
                                    ][0]["id"],
                                    "group_id": self._classes[0]["attribute_groups"][0][
                                        "id"
                                    ],
                                }
                            }
                        ],
                    },
                    {
                        "class_id": self._classes[1]["id"],
                        "attribute": [
                            {
                                "attribute": {
                                    "id": self._classes[1]["attribute_groups"][0][
                                        "attributes"
                                    ][0]["id"],
                                    "group_id": self._classes[1]["attribute_groups"][0][
                                        "id"
                                    ],
                                }
                            }
                        ],
                    },
                ],
                connections=[[1, 2]],
            )

        with self.assertRaisesRegexp(AppException, "Invalid steps provided."):
            sa.set_project_steps(
                self.PROJECT_NAME,
                steps=[
                    {
                        "class_id": self._classes[1]["id"],
                        "attribute": [
                            {
                                "attribute": {
                                    "id": self._classes[0]["attribute_groups"][0][
                                        "attributes"
                                    ][0]["id"],
                                    "group_id": 1,
                                }  # invalid group id
                            }
                        ],
                    },
                    {
                        "class_id": self._classes[1]["id"],
                        "attribute": [
                            {
                                "attribute": {
                                    "id": self._classes[1]["attribute_groups"][0][
                                        "attributes"
                                    ][0]["id"],
                                    "group_id": self._classes[1]["attribute_groups"][0][
                                        "id"
                                    ],
                                }
                            }
                        ],
                    },
                ],
                connections=[[1, 2]],
            )

        with self.assertRaisesRegexp(AppException, "Invalid steps provided."):
            sa.set_project_steps(
                self.PROJECT_NAME,
                steps=[
                    {
                        "class_id": self._classes[1]["id"],
                        "attribute": [
                            {
                                "attribute": {
                                    "id": 1,  # invalid attr id
                                    "group_id": self._classes[0]["attribute_groups"][0][
                                        "id"
                                    ],
                                }
                            }
                        ],
                    },
                    {
                        "class_id": self._classes[1]["id"],
                        "attribute": [
                            {
                                "attribute": {
                                    "id": self._classes[1]["attribute_groups"][0][
                                        "attributes"
                                    ][0]["id"],
                                    "group_id": self._classes[1]["attribute_groups"][0][
                                        "id"
                                    ],
                                }
                            }
                        ],
                    },
                ],
                connections=[[1, 2]],
            )

    def test_create_invalid_connection(self):
        args = (
            self.PROJECT_NAME,
            [
                {
                    "class_id": self._classes[0]["id"],
                    "attribute": [
                        {
                            "attribute": {
                                "id": self._classes[0]["attribute_groups"][0][
                                    "attributes"
                                ][0]["id"],
                                "group_id": self._classes[0]["attribute_groups"][0][
                                    "id"
                                ],
                            }
                        }
                    ],
                },
                {
                    "class_id": self._classes[1]["id"],
                    "attribute": [
                        {
                            "attribute": {
                                "id": self._classes[1]["attribute_groups"][0][
                                    "attributes"
                                ][0]["id"],
                                "group_id": self._classes[1]["attribute_groups"][0][
                                    "id"
                                ],
                            }
                        }
                    ],
                },
            ],
        )
        with self.assertRaisesRegexp(
            AppException, "Invalid connections: duplicates in a connection group."
        ):
            sa.set_project_steps(
                *args,
                connections=[
                    [1, 2],
                    [2, 1],
                ]
            )
        with self.assertRaisesRegexp(
            AppException, "Invalid connections: index out of allowed range."
        ):
            sa.set_project_steps(*args, connections=[[1, 3]])
