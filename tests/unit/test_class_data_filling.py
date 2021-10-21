from unittest import TestCase

from src.superannotate.lib.core.helpers import fill_annotation_ids


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


class TestClassData(TestCase):

    def test_map_annotation_classes_name(self):
        annotation_classes_name_maps = {
            "Personal vehicle": {"id": 72274, "attribute_groups": {"Num doors": {"id": 28230, "attributes": {"2": 117845}}}}}
        fill_annotation_ids(TEST_ANNOTATION, annotation_classes_name_maps, [])
        attribute = TEST_ANNOTATION["instances"][0]["attributes"][0]
        self.assertEqual(TEST_ANNOTATION["instances"][0]["classId"], 72274)
        self.assertEqual(attribute["id"], 117845)
        self.assertEqual(attribute["groupId"], 28230)
