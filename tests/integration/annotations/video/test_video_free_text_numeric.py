import json
import os

from src.superannotate import SAClient
from tests import DATA_SET_PATH
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestUploadVideoFreNumAnnotation(BaseTestCase):
    PROJECT_NAME = "video annotation upload with ree text and numeric"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Video"
    ANNOTATIONS_PATH = "sample_video_num_free_text"
    ITEM_NAME = "sample_video.mp4"
    CLASSES_PATH = "classes/classes.json"

    @property
    def folder_path(self):
        return os.path.join(DATA_SET_PATH, self.ANNOTATIONS_PATH)

    def test_upload(self):
        sa.attach_items(
            self.PROJECT_NAME, [{"url": "sad", "name": self.ITEM_NAME}]
        )  # noqa
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, os.path.join(self.folder_path, self.CLASSES_PATH)
        )
        (
            uploaded_annotations,
            failed_annotations,
            missing_annotations,
        ) = sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path
        )
        self.assertEqual(len(uploaded_annotations), 1)
        self.assertEqual(len(failed_annotations), 0)
        self.assertEqual(len(missing_annotations), 0)
        annotation = sa.get_annotations(self.PROJECT_NAME)[0]
        local_annotation = json.load(
            open(os.path.join(self.folder_path, (self.ITEM_NAME + ".json")))
        )
        assert len(annotation["instances"]) == len(local_annotation["instances"])
