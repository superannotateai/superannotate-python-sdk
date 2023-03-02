import json
import math
import os

from src.superannotate import SAClient
from tests import DATA_SET_PATH
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestGetAnnotations(BaseTestCase):
    PROJECT_NAME = "test attach video urls"
    PATH_TO_URLS = "attach_video_for_annotation.csv"
    PATH_TO_URLS_WITHOUT_NAMES = "attach_urls_with_no_name.csv"
    PROJECT_DESCRIPTION = "desc"
    ANNOTATIONS_PATH = "video_convertor_annotations"
    VIDEO_NAME = "video.mp4"
    CLASSES_PATH = "video_annotation/classes/classes.json"
    PROJECT_TYPE = "Video"

    @property
    def csv_path(self):
        return os.path.join(DATA_SET_PATH, self.PATH_TO_URLS)

    @property
    def classes_path(self):
        return os.path.join(DATA_SET_PATH, self.CLASSES_PATH)

    @property
    def annotations_path(self):
        return os.path.join(DATA_SET_PATH, self.ANNOTATIONS_PATH)

    def test_video_annotation_upload(self):
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.classes_path
        )

        _, _, _ = sa.attach_items(
            self.PROJECT_NAME,
            self.csv_path,
        )
        sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.annotations_path
        )
        with self.assertLogs("sa") as cm:
            annotations = sa.get_annotations_per_frame(
                self.PROJECT_NAME, self.VIDEO_NAME, 1
            )
            self.assertEqual(
                len(annotations),
                int(
                    math.ceil(
                        json.load(
                            open(f"{self.annotations_path}/{self.VIDEO_NAME}.json")
                        )["metadata"]["duration"]
                        / (1000 * 1000)
                    )
                ),
            )
            assert (
                "INFO:sa:Getting annotations for 31 frames from video.mp4."
                == cm.output[0]
            )
            assert len(cm.output) == 1
