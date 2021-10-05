import os
from os.path import dirname

import src.superannotate as sa
from tests.integration.base import BaseTestCase


class TestUploadVideoAnnotation(BaseTestCase):
    PROJECT_NAME = "video annotation upload"
    PATH_TO_URLS = "data_set/attach_video_for_annotation.csv"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Video"
    ANNOTATIONS_PATH = "data_set/video_annotation"
    CLASSES_PATH = "data_set/video_annotation/classes/classes.json"

    @property
    def csv_path(self):
        return os.path.join(dirname(dirname(__file__)), self.PATH_TO_URLS)

    @property
    def annotations_path(self):
        return os.path.join(dirname(dirname(__file__)), self.ANNOTATIONS_PATH)

    @property
    def classes_path(self):
        return os.path.join(dirname(dirname(__file__)), self.CLASSES_PATH)

    def test_video_annotation_upload(self):
        sa.create_annotation_classes_from_classes_json(self.PROJECT_NAME, self.classes_path)

        uploaded, could_not_upload, existing_images = sa.attach_video_urls_to_project(
            self.PROJECT_NAME,
            self.csv_path,
        )
        sa.upload_annotations_from_folder_to_project(self.PROJECT_NAME, self.annotations_path)
        print("yp")


