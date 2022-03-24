import time
import copy
from unittest import TestCase

from src.superannotate.lib.core.data_handlers import MissingIDsHandler
from src.superannotate.lib.core.data_handlers import LastActionHandler
from src.superannotate.lib.core.reporter import Reporter
from superannotate_schemas.schemas.classes import AnnotationClass

import pytest


CLASSES_PAYLOAD = [
    {
        'id': 876855,
        'createdAt': '2021-10-26T14:08:06.000Z',
        'updatedAt': '2021-10-26T14:08:06.000Z',
        'color': '#fe62e2',
        'count': 0,
        'name': 'Personal vehicle',
        'project_id': 163549,
        'attribute_groups': [
            {
                'id': 350510,
                'class_id': 876855,
                'name': 'Num doors',
                'is_multiselect': 0,
                'createdAt': '2021-10-26T14:08:08.000Z',
                'updatedAt': '2021-10-26T14:08:08.000Z',
                'attributes': [
                    {
                        'id': 1208404,
                        'group_id': 350510,
                        'project_id': 163549,
                        'name': '2',
                        'count': 0,
                        'createdAt': '2021-10-26T14:10:25.000Z',
                        'updatedAt': '2021-10-26T14:10:25.000Z'
                    },
                    {
                        'id': 1208410,
                        'group_id': 350510,
                        'project_id': 163549,
                        'name': 'ab',
                        'count': 0,
                        'createdAt': '2021-10-26T14:12:29.000Z',
                        'updatedAt': '2021-10-26T14:12:29.000Z'
                    }
                ]
            },
            {
                'id': 350519,
                'class_id': 876855,
                'name': 'ab',
                'is_multiselect': 0,
                'createdAt': '2021-10-26T14:12:41.000Z',
                'updatedAt': '2021-10-26T14:12:41.000Z',
                'attributes': [
                    {
                        'id': 1208411,
                        'group_id': 350519,
                        'project_id': 163549,
                        'name': 'aabb',
                        'count': 0,
                        'createdAt': '2021-10-26T14:12:44.000Z',
                        'updatedAt': '2021-10-26T14:12:44.000Z'
                    }
                ]
            }
        ]
    },
    {
        'id': 876856,
        'createdAt': '2021-10-26T14:08:12.000Z',
        'updatedAt': '2021-10-26T14:08:12.000Z',
        'color': '#9807f8',
        'count': 0,
        'name': 'b',
        'project_id': 163549,
        'attribute_groups': [
            {
                'id': 350514,
                'class_id': 876856,
                'name': 'bb',
                'is_multiselect': 0,
                'createdAt': '2021-10-26T14:10:29.000Z',
                'updatedAt': '2021-10-26T14:10:29.000Z',
                'attributes': [
                    {
                        'id': 1208405,
                        'group_id': 350514,
                        'project_id': 163549,
                        'name': 'bbb',
                        'count': 0,
                        'createdAt': '2021-10-26T14:10:31.000Z',
                        'updatedAt': '2021-10-26T14:10:31.000Z'
                    }
                ]
            }
        ]
    },
    {
        'id': 878485,
        'createdAt': '2021-10-28T12:18:53.000Z',
        'updatedAt': '2021-10-28T12:18:53.000Z',
        'color': '#53a815',
        'count': 0,
        'name': 'class1',
        'project_id': 163549,
        'attribute_groups': [
            {
                'id': 351454,
                'class_id': 878485,
                'name': 'cl1gr1',
                'is_multiselect': 0,
                'createdAt': '2021-10-28T12:18:53.000Z',
                'updatedAt': '2021-10-28T12:18:53.000Z',
                'attributes': [
                    {
                        'id': 1209955,
                        'group_id': 351454,
                        'project_id': 163549,
                        'name': 'att1',
                        'count': 0,
                        'createdAt': '2021-10-28T12:18:53.000Z',
                        'updatedAt': '2021-10-28T12:18:53.000Z'
                    },
                    {
                        'id': 1209956,
                        'group_id': 351454,
                        'project_id': 163549,
                        'name': 'att2',
                        'count': 0,
                        'createdAt': '2021-10-28T12:18:53.000Z',
                        'updatedAt': '2021-10-28T12:18:53.000Z'
                    },
                    {
                        'id': 1209957,
                        'group_id': 351454,
                        'project_id': 163549,
                        'name': 'att3',
                        'count': 0,
                        'createdAt': '2021-10-28T12:18:53.000Z',
                        'updatedAt': '2021-10-28T12:18:53.000Z'
                    }
                ]
            },
            {
                'id': 351455,
                'class_id': 878485,
                'name': 'cl1gr2',
                'is_multiselect': 1,
                'createdAt': '2021-10-28T12:18:53.000Z',
                'updatedAt': '2021-10-28T12:18:53.000Z',
                'attributes': [
                    {
                        'id': 1209958,
                        'group_id': 351455,
                        'project_id': 163549,
                        'name': 'multi1',
                        'count': 0,
                        'createdAt': '2021-10-28T12:18:53.000Z',
                        'updatedAt': '2021-10-28T12:18:53.000Z'
                    },
                    {
                        'id': 1209959,
                        'group_id': 351455,
                        'project_id': 163549,
                        'name': 'multi2',
                        'count': 0,
                        'createdAt': '2021-10-28T12:18:53.000Z',
                        'updatedAt': '2021-10-28T12:18:53.000Z'
                    },
                    {
                        'id': 1209960,
                        'group_id': 351455,
                        'project_id': 163549,
                        'name': 'multi3',
                        'count': 0,
                        'createdAt': '2021-10-28T12:18:53.000Z',
                        'updatedAt': '2021-10-28T12:18:53.000Z'
                    }
                ]
            }
        ]
    },
    {
        'id': 878486,
        'createdAt': '2021-10-28T12:18:53.000Z',
        'updatedAt': '2021-10-28T12:18:53.000Z',
        'color': '#64ef6e',
        'count': 0,
        'name': 'class2',
        'project_id': 163549,
        'attribute_groups': [

        ]
    },
    {
        'id': 878487,
        'createdAt': '2021-10-28T12:18:53.000Z',
        'updatedAt': '2021-10-28T12:18:53.000Z',
        'color': '#64ef6e',
        'count': 0,
        'name': 'TagAnnotationClass',
        'type': 'tag',
        'project_id': 163549,
        'attribute_groups': [
            {
                'id': 350514,
                'class_id': 876857,
                'name': 'TagAnnotationGroup',
                'is_multiselect': 0,
                'createdAt': '2021-10-26T14:10:29.000Z',
                'updatedAt': '2021-10-26T14:10:29.000Z',
                'attributes': [
                    {
                        'id': 1208405,
                        'group_id': 350514,
                        'project_id': 163549,
                        'name': 'TagAnnotationAttribute',
                        'count': 0,
                        'createdAt': '2021-10-26T14:10:31.000Z',
                        'updatedAt': '2021-10-26T14:10:31.000Z'
                    }
                ]
            }
        ]
    }
]


class TestClassData(TestCase):
    TEST_ANNOTATION = {
        "metadata": {
            "name": "example_image_1.jpg",
            "width": 1024,
            "height": 683,
        },
        "instances": [
            {
                "type": "bbox",
                "probability": 100,
                "points": {
                    "x1": 437.16,
                    "x2": 465.23,
                    "y1": 341.5,
                    "y2": 357.09
                },
                "pointLabels": {},
                "attributes": [
                    {
                        "name": "2",
                        "groupName": "Num doors"
                    }
                ],
                "className": "Personal vehicle"
            }
        ]
    }

    @property
    def annotation_data(self):
        return copy.copy(self.TEST_ANNOTATION)

    def test_annotation_tags_filling(self):
        annotation_classes = [AnnotationClass(**class_data) for class_data in CLASSES_PAYLOAD]
        handler = MissingIDsHandler(annotation_classes, [], Reporter())
        annotation_data = self.annotation_data
        annotation_data["instances"].append(
            {
                "type": "tag",
                "probability": 100,
                "points": {
                    "x1": 437.16,
                    "x2": 465.23,
                    "y1": 341.5,
                    "y2": 357.09
                },
                "pointLabels": {},
                "attributes": [
                    {
                        "name": "TagAnnotationAttribute",
                        "groupName": "TagAnnotationAttribute"
                    }
                ],
                "className": "TagAnnotationClass",
                'color': '#fe62e2'
            }
        )
        processed_data = handler.handle(annotation_data)
        self.assertEqual(processed_data["instances"][-1]["classId"], 878487)

    @pytest.mark.skip(reason="Need to adjust")
    def test_annotation_filling_with_duplicated_tag_object_class_names(self):
        annotation_classes = [AnnotationClass(**class_data) for class_data in CLASSES_PAYLOAD]
        annotation_class = AnnotationClass(**CLASSES_PAYLOAD[-1])
        annotation_class.type = "object"
        annotation_class.id = 700
        annotation_classes.append(annotation_class)
        handler = MissingIDsHandler(annotation_classes, [], Reporter())
        annotation_data = copy.copy(self.annotation_data)
        annotation_data["instances"].append(
            {
                "type": "object",
                "probability": 100,
                "points": {
                    "x1": 437.16,
                    "x2": 465.23,
                    "y1": 341.5,
                    "y2": 357.09
                },
                "pointLabels": {},
                "attributes": [
                    {
                        "name": "TagAnnotationAttribute",
                        "groupName": "TagAnnotationAttribute"
                    }
                ],
                "className": "TagAnnotationClass"
            }
        )
        processed_data = handler.handle(annotation_data)
        self.assertEqual(processed_data["instances"][-1]["classId"], 700)

    def test_missing_ids_filling(self):
        annotation_classes = [AnnotationClass(**class_data) for class_data in CLASSES_PAYLOAD]
        handler = MissingIDsHandler(annotation_classes, [], Reporter())

        test_annotation = handler.handle(self.annotation_data)
        attribute = test_annotation["instances"][0]["attributes"][0]
        self.assertEqual(test_annotation["instances"][0]["classId"], 876855)
        self.assertEqual(attribute["groupId"], 350510)
        self.assertEqual(attribute["id"], 1208404)

    def test_last_action_filling(self):
        handler = LastActionHandler("hello@superannotate.com")
        handler.handle(self.annotation_data)
        self.assertEqual(
            self.TEST_ANNOTATION["metadata"]["lastAction"],
            {"email": "hello@superannotate.com", "timestamp": int(time.time())}
        )
