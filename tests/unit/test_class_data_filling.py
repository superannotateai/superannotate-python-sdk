import time
from unittest import TestCase

from src.superannotate.lib.core.helpers import fill_annotation_ids
from src.superannotate.lib.core.helpers import handle_last_action
from src.superannotate.lib.core.helpers import map_annotation_classes_name
from src.superannotate.lib.core.reporter import Reporter
from src.superannotate.lib.core.entities import TeamEntity
from src.superannotate.lib.infrastructure.repositories import AnnotationClassRepository


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

CLASSES_PAYLOAD = [
    {'id': 876855, 'createdAt': '2021-10-26T14:08:06.000Z', 'updatedAt': '2021-10-26T14:08:06.000Z', 'color': '#fe62e2',
     'count': 0, 'name': 'a', 'project_id': 163549, 'attribute_groups': [
        {'id': 350510, 'class_id': 876855, 'name': 'aa', 'is_multiselect': 0, 'createdAt': '2021-10-26T14:08:08.000Z',
         'updatedAt': '2021-10-26T14:08:08.000Z', 'attributes': [
            {'id': 1208404, 'group_id': 350510, 'project_id': 163549, 'name': 'aaa', 'count': 0,
             'createdAt': '2021-10-26T14:10:25.000Z', 'updatedAt': '2021-10-26T14:10:25.000Z'},
            {'id': 1208410, 'group_id': 350510, 'project_id': 163549, 'name': 'ab', 'count': 0,
             'createdAt': '2021-10-26T14:12:29.000Z', 'updatedAt': '2021-10-26T14:12:29.000Z'}]},
        {'id': 350519, 'class_id': 876855, 'name': 'ab', 'is_multiselect': 0, 'createdAt': '2021-10-26T14:12:41.000Z',
         'updatedAt': '2021-10-26T14:12:41.000Z', 'attributes': [
            {'id': 1208411, 'group_id': 350519, 'project_id': 163549, 'name': 'aabb', 'count': 0,
             'createdAt': '2021-10-26T14:12:44.000Z', 'updatedAt': '2021-10-26T14:12:44.000Z'}]}]},
    {'id': 876856, 'createdAt': '2021-10-26T14:08:12.000Z', 'updatedAt': '2021-10-26T14:08:12.000Z', 'color': '#9807f8',
     'count': 0, 'name': 'b', 'project_id': 163549, 'attribute_groups': [
        {'id': 350514, 'class_id': 876856, 'name': 'bb', 'is_multiselect': 0, 'createdAt': '2021-10-26T14:10:29.000Z',
         'updatedAt': '2021-10-26T14:10:29.000Z', 'attributes': [
            {'id': 1208405, 'group_id': 350514, 'project_id': 163549, 'name': 'bbb', 'count': 0,
             'createdAt': '2021-10-26T14:10:31.000Z', 'updatedAt': '2021-10-26T14:10:31.000Z'}]}]},
    {'id': 878485, 'createdAt': '2021-10-28T12:18:53.000Z', 'updatedAt': '2021-10-28T12:18:53.000Z', 'color': '#53a815',
     'count': 0, 'name': 'class1', 'project_id': 163549, 'attribute_groups': [
        {'id': 351454, 'class_id': 878485, 'name': 'cl1gr1', 'is_multiselect': 0,
         'createdAt': '2021-10-28T12:18:53.000Z', 'updatedAt': '2021-10-28T12:18:53.000Z', 'attributes': [
            {'id': 1209955, 'group_id': 351454, 'project_id': 163549, 'name': 'att1', 'count': 0,
             'createdAt': '2021-10-28T12:18:53.000Z', 'updatedAt': '2021-10-28T12:18:53.000Z'},
            {'id': 1209956, 'group_id': 351454, 'project_id': 163549, 'name': 'att2', 'count': 0,
             'createdAt': '2021-10-28T12:18:53.000Z', 'updatedAt': '2021-10-28T12:18:53.000Z'},
            {'id': 1209957, 'group_id': 351454, 'project_id': 163549, 'name': 'att3', 'count': 0,
             'createdAt': '2021-10-28T12:18:53.000Z', 'updatedAt': '2021-10-28T12:18:53.000Z'}]},
        {'id': 351455, 'class_id': 878485, 'name': 'cl1gr2', 'is_multiselect': 1,
         'createdAt': '2021-10-28T12:18:53.000Z', 'updatedAt': '2021-10-28T12:18:53.000Z', 'attributes': [
            {'id': 1209958, 'group_id': 351455, 'project_id': 163549, 'name': 'multi1', 'count': 0,
             'createdAt': '2021-10-28T12:18:53.000Z', 'updatedAt': '2021-10-28T12:18:53.000Z'},
            {'id': 1209959, 'group_id': 351455, 'project_id': 163549, 'name': 'multi2', 'count': 0,
             'createdAt': '2021-10-28T12:18:53.000Z', 'updatedAt': '2021-10-28T12:18:53.000Z'},
            {'id': 1209960, 'group_id': 351455, 'project_id': 163549, 'name': 'multi3', 'count': 0,
             'createdAt': '2021-10-28T12:18:53.000Z', 'updatedAt': '2021-10-28T12:18:53.000Z'}]}]},
    {'id': 878486, 'createdAt': '2021-10-28T12:18:53.000Z', 'updatedAt': '2021-10-28T12:18:53.000Z', 'color': '#64ef6e',
     'count': 0, 'name': 'class2', 'project_id': 163549, 'attribute_groups': []}]


class TestClassData(TestCase):

    def test_annotation_classes_name_maps(self):
        classes = [AnnotationClassRepository.dict2entity(i) for i in CLASSES_PAYLOAD]
        mapped_data = map_annotation_classes_name(classes, Reporter())

        self.assertEqual(4, len(mapped_data.keys()))
        self.assertEqual(2, len(mapped_data["class1"]["attribute_groups"]))
        self.assertEqual(350510, mapped_data["a"]["attribute_groups"]["aa"]["id"])

    def test_map_annotation_classes_name(self):
        annotation_classes_name_maps = {
            "Personal vehicle": {"id": 72274,
                                 "attribute_groups": {"Num doors": {"id": 28230, "attributes": {"2": 117845}}}}}
        fill_annotation_ids(TEST_ANNOTATION, annotation_classes_name_maps, [], Reporter())
        attribute = TEST_ANNOTATION["instances"][0]["attributes"][0]
        self.assertEqual(TEST_ANNOTATION["instances"][0]["classId"], 72274)
        self.assertEqual(attribute["id"], 117845)
        self.assertEqual(attribute["groupId"], 28230)

    def test_last_action_filling(self):
        handle_last_action(TEST_ANNOTATION, TeamEntity(creator_id="Hello"))
        self.assertEqual(
            TEST_ANNOTATION["metadata"]["lastAction"],
            {"email": "Hello", "timestamp": int(time.time())}
        )