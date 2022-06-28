import json
import os
import tempfile
from pathlib import Path

from src.superannotate import SAClient
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestAnnotationAdding(BaseTestCase):
    PROJECT_NAME = "test_annotations_adding"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    TEST_INVALID_ANNOTATION_FOLDER_PATH = "data_set/sample_project_vector_invalid"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"
    EXAMPLE_IMAGE_1 = "example_image_1.jpg"
    EXAMPLE_IMAGE_2 = "example_image_2.jpg"

    @property
    def folder_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.TEST_FOLDER_PATH)

    @property
    def invalid_json_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.TEST_INVALID_ANNOTATION_FOLDER_PATH)

    @property
    def classes_json_path(self):
        return f"{self.folder_path}/classes/classes.json"

    def test_upload_invalid_annotations(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        uploaded_annotations, failed_annotations, missing_annotations = sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.invalid_json_path
        )
        self.assertEqual(len(uploaded_annotations), 3)
        self.assertEqual(len(failed_annotations), 1)
        self.assertEqual(len(missing_annotations), 0)

    def test_upload_annotations(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path
        )

    def test_add_point_to_empty_image(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )

        sa.add_annotation_point_to_image(
            self.PROJECT_NAME, self.EXAMPLE_IMAGE_1, [250, 250], "test_add"
        )
        annotations_new = sa.get_annotations(self.PROJECT_NAME, [self.EXAMPLE_IMAGE_1])[0]

        del annotations_new["instances"][0]['createdAt']
        del annotations_new["instances"][0]['updatedAt']

        self.assertEqual(
            annotations_new["instances"][0], {
                'x': 250.0,
                'y': 250.0,
                'creationType': 'Preannotation',
                'visible': True,
                'locked': False,
                'probability': 100,
                'attributes': [],
                'type': 'point',
                'pointLabels': {},
                'groupId': 0,
                'classId': -1,
            }
        )

    def test_add_bbox_to_empty_annotation(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )

        sa.add_annotation_bbox_to_image(
            self.PROJECT_NAME, self.EXAMPLE_IMAGE_1, [10, 10, 500, 100], "test_add"
        )

        annotations_new = sa.get_annotations(self.PROJECT_NAME, [self.EXAMPLE_IMAGE_1])[0]

        del annotations_new["instances"][0]['createdAt']
        del annotations_new["instances"][0]['updatedAt']

        self.assertEqual(annotations_new['instances'][0], {
            'creationType': 'Preannotation',
            'visible': True,
            'locked': False,
            'probability': 100,
            'attributes': [],
            'type': 'bbox',
            'pointLabels': {},
            'groupId': 0,
            'points': {'x1': 10.0, 'x2': 500.0, 'y1': 10.0, 'y2': 100.0},
            'classId': -1,
        })

    def test_add_comment_to_empty_annotation(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )

        sa.add_annotation_comment_to_image(self.PROJECT_NAME, self.EXAMPLE_IMAGE_1, "some comment", [1, 2],
                                           "abc@abc.com")

        annotations_new = sa.get_annotations(self.PROJECT_NAME, [self.EXAMPLE_IMAGE_1])[0]

        annotations_new['comments'][0]['createdAt'] = ""
        annotations_new['comments'][0]['updatedAt'] = ""

        self.assertEqual(annotations_new['comments'][0],
                         {'createdBy': {'email': 'abc@abc.com', 'role': 'Admin'},
                          'updatedBy': {'email': 'abc@abc.com', 'role': 'Admin'},
                          'creationType': 'Preannotation',
                          'createdAt': '',
                          'updatedAt': '',
                          'x': 1.0, 'y': 2.0,
                          'resolved': False,
                          'correspondence': [{'text': 'some comment', 'email': 'abc@abc.com'}]
                          })

    def test_add_bbox(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.classes_json_path
        )
        sa.create_annotation_class(
            self.PROJECT_NAME,
            "test_add",
            "#FF0000",
            [{"name": "height", "attributes": [{"name": "tall"}, {"name": "short"}]}],
        )
        sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path
        )

        annotations = sa.get_annotations(self.PROJECT_NAME, [self.EXAMPLE_IMAGE_1])[0]

        sa.add_annotation_bbox_to_image(
            self.PROJECT_NAME, self.EXAMPLE_IMAGE_1, [10, 10, 500, 100], "test_add"
        )
        sa.add_annotation_point_to_image(
            self.PROJECT_NAME, self.EXAMPLE_IMAGE_1, [250, 250], "test_add"
        )
        sa.add_annotation_comment_to_image(
            self.PROJECT_NAME,
            self.EXAMPLE_IMAGE_1,
            "Hello World",
            [100, 100],
            "super@annotate.com",
            True,
        )
        annotations_new = sa.get_annotations(self.PROJECT_NAME, [self.EXAMPLE_IMAGE_1])[0]
        with tempfile.TemporaryDirectory() as tmpdir_name:
            json.dump(annotations_new, open(f"{tmpdir_name}/new_anns.json", "w"))
            self.assertEqual(
                len(annotations_new["instances"]) + len(annotations_new["comments"]),
                len(annotations["instances"]) + len(annotations["comments"]) + 3,
            )

    def test_add_bbox_no_init(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.classes_json_path
        )
        sa.create_annotation_class(self.PROJECT_NAME, "test_add", "#FF0000")
        sa.add_annotation_bbox_to_image(
            self.PROJECT_NAME, self.EXAMPLE_IMAGE_1, [10, 10, 500, 100], "test_add"
        )
        annotations_new = sa.get_annotations(self.PROJECT_NAME, [self.EXAMPLE_IMAGE_1])[0]

        self.assertEqual(len(annotations_new["instances"]), 1)

        export = sa.prepare_export(self.PROJECT_NAME, include_fuse=True)
        with tempfile.TemporaryDirectory() as tmpdir_name:
            sa.download_export(self.PROJECT_NAME, export["name"], tmpdir_name)

            non_empty_annotations = 0
            json_files = Path(tmpdir_name).glob("*.json")
            for json_file in json_files:
                json_ann = json.load(open(json_file))
                if "instances" in json_ann and len(json_ann["instances"]) > 0:
                    non_empty_annotations += 1
                    self.assertEqual(len(json_ann["instances"]), 1)

            self.assertEqual(non_empty_annotations, 1)

    def test_add_bbox_json(self):
        with tempfile.TemporaryDirectory() as tmpdir_name:
            dest = Path(f"{tmpdir_name}/test.json")
            source = Path(f"{self.folder_path}/{self.EXAMPLE_IMAGE_1}___objects.json")

            dest.write_text(source.read_text())
            annotations = json.load(open(dest))
            annotations_new = json.load(open(dest))

            self.assertEqual(
                len(annotations_new["instances"]), len(annotations["instances"])
            )
            self.assertEqual(
                len(annotations_new["comments"]), len(annotations["comments"])
            )

    def test_add_bbox_with_dict(self):
        sa.upload_image_to_project(self.PROJECT_NAME, f"{self.folder_path}/{self.EXAMPLE_IMAGE_1}")
        sa.create_annotation_class(
            self.PROJECT_NAME,
            "test_add",
            "#FF0000",
            [{"name": "test", "attributes": [{"name": "yes"}, {"name": "no"}]}]
        )
        sa.add_annotation_bbox_to_image(
            project=self.PROJECT_NAME,
            image_name=self.EXAMPLE_IMAGE_1,
            bbox=[10, 20, 100, 150],
            annotation_class_name="test_add",
            annotation_class_attributes=[{'name': 'yes', 'groupName': 'test'}]
        )
        annotation = sa.get_annotations(self.PROJECT_NAME, [self.EXAMPLE_IMAGE_1])[0]
        self.assertTrue(
            all([annotation["instances"][0]["attributes"][0][key] == val for key, val in
                 {'name': 'yes', 'groupName': 'test'}.items()])
        )
