import os
import random
from pathlib import Path
from unittest import TestCase

from superannotate_schemas.schemas.classes import AnnotationClass
from superannotate_schemas.schemas.classes import Attribute
from superannotate_schemas.schemas.classes import AttributeGroup

from src.superannotate.lib.core.data_handlers import VideoFormatHandler
from src.superannotate.lib.core.reporter import Reporter


TEST_ANNOTATION = {
    "metadata": {
        "name": "video.mp4",
        "width": 480,
        "height": 270,
        "status": "NotStarted",
        "url": "https://file-examples-com.github.io/uploads/2017/04/file_example_MP4_480_1_5MG.mp4",
        "duration": 30526667,
        "projectId": 152038,
        "error": None,
        "annotatorEmail": None,
        "qaEmail": None
    },
    "instances": [
        {
            "meta": {
                "type": "bbox",
                "className": "vid",
                "pointLabels": {
                    "3": "point label bro"
                },
                "start": 0,
                "end": 30526667
            },
            "parameters": [
                {
                    "start": 0,
                    "end": 30526667,
                    "timestamps": [
                        {
                            "points": {
                                "x1": 223.32,
                                "y1": 78.45,
                                "x2": 312.31,
                                "y2": 176.66
                            },
                            "timestamp": 0,
                            "attributes": []
                        },
                        {
                            "points": {
                                "x1": 182.08,
                                "y1": 33.18,
                                "x2": 283.45,
                                "y2": 131.39
                            },
                            "timestamp": 17271058,
                            "attributes": [
                                {
                                    "name": "attr",
                                    "groupName": "attr g"
                                },
                            ]
                        },
                        {
                            "points": {
                                "x1": 182.32,
                                "y1": 36.33,
                                "x2": 284.01,
                                "y2": 134.54
                            },
                            "timestamp": 18271058,
                            "attributes": []
                        },
                        {
                            "points": {
                                "x1": 182.32,
                                "y1": 36.33,
                                "x2": 284.01,
                                "y2": 134.54
                            },
                            "timestamp": 18271358,
                            "attributes": [
                                {
                                    "name": "attr",
                                    "groupName": "attr b"
                                },
                                {
                                    "name": "attr",
                                    "groupName": "attr g"
                                },
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "meta": {
                "type": "bbox",
                "className": "vid",
                "pointLabels": {
                    "3": "point label bro"
                },
                "start": 0,
                "end": 30526667
            },
            "parameters": [
                {
                    "start": 0,
                    "end": 30526667,
                    "timestamps": [
                        {
                            "points": {
                                "x1": 223.32,
                                "y1": 78.45,
                                "x2": 312.31,
                                "y2": 176.66
                            },
                            "timestamp": 0,
                            "attributes": []
                        },
                        {
                            "points": {
                                "x1": 182.08,
                                "y1": 33.18,
                                "x2": 283.45,
                                "y2": 131.39
                            },
                            "timestamp": 17271058,
                            "attributes": [
                                {
                                    "name": "attr",
                                    "groupName": "attr b"
                                }
                            ]
                        },
                        {
                            "points": {
                                "x1": 182.32,
                                "y1": 36.33,
                                "x2": 284.01,
                                "y2": 134.54
                            },
                            "timestamp": 18271058,
                            "attributes": []
                        },
                        {
                            "points": {
                                "x1": 182.32,
                                "y1": 36.33,
                                "x2": 284.01,
                                "y2": 134.54
                            },
                            "timestamp": 18271358,
                            "attributes": [
                                {
                                    "name": "attr a",
                                    "groupName": "attr b"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    ],
    "tags": [
        "some tag"
    ]
}


class TestClassData(TestCase):
    ANNOTATIONS_PATH = "data_set/video_annotation"

    def __init__(self, *args, **kwargs):
        super(TestClassData, self).__init__(*args, **kwargs)
        self.annotation_classes = [
            AnnotationClass(
                id=1,
                name="vid",
                color=f"#{random.randint(0, 0xFFFFFF):06x}",
                attribute_groups=[
                    AttributeGroup(
                        id=2,
                        name="attr g",
                        attributes=[
                            Attribute(id=4, name="attr")
                        ]
                    ),
                    AttributeGroup(
                        id=3,
                        name="attr b",
                        attributes=[
                            Attribute(id=5, name="attr"),
                            Attribute(id=6, name="attr a"),
                        ]
                    )
                ]
            )
        ]

    @property
    def folder_path(self):
        return Path(__file__).parent.parent.parent

    @property
    def annotations_path(self):
        return os.path.join(self.folder_path, self.ANNOTATIONS_PATH)

    def test_map_annotation_classes_name(self):
        handler = VideoFormatHandler(self.annotation_classes, Reporter())

        annotation = handler.handle(TEST_ANNOTATION)
        timestamps = [i["timestamp"] for i in TEST_ANNOTATION["instances"][0]["parameters"][0]["timestamps"]]
        first_instance_timeline = annotation["instances"][0]["timeline"]
        second_instance_timeline = annotation["instances"][1]["timeline"]

        self.assertEqual(first_instance_timeline[timestamps[1] / 10 ** 6]["attributes"]["+"][0],
                         {'id': 4, 'groupId': 2})
        self.assertEqual(first_instance_timeline[timestamps[2] / 10 ** 6]["attributes"]["-"][0],
                         {'id': 4, 'groupId': 2})
        self.assertIn({'id': 4, 'groupId': 2}, first_instance_timeline[timestamps[3] / 10 ** 6]["attributes"]["+"])
        self.assertIn({'id': 5, 'groupId': 3}, first_instance_timeline[timestamps[3] / 10 ** 6]["attributes"]["+"])

        self.assertEqual(second_instance_timeline[timestamps[1] / 10 ** 6]["attributes"]["+"][0],
                         {'id': 5, 'groupId': 3})
        self.assertEqual(second_instance_timeline[timestamps[2] / 10 ** 6]["attributes"]["-"][0],
                         {'id': 5, 'groupId': 3})
        self.assertEqual(second_instance_timeline[timestamps[3] / 10 ** 6]["attributes"]["+"][0],
                         {'id': 6, 'groupId': 3})

    def test_empty_exported_annotations(self):
        annotation_json = {"metadata": {"name": "1gb", "status": "NotStarted",
                                        "url": "https://drive.google.com/uc?export=download&id=14R6IXioDzC8mH52uIsyhNownbBji5TEl",
                                        "duration": None, "projectId": 164746, "error": None, "annotatorEmail": None,
                                        "qaEmail": None}, "instances": [], "tags": []}
        handler = VideoFormatHandler(self.annotation_classes, Reporter())

        _ = handler.handle(annotation_json)
