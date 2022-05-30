import json
import os
from os.path import dirname
from pathlib import Path
from typing import List

import pytest
from pydantic import parse_obj_as
from superannotate_schemas.schemas.internal import VectorAnnotation

from src.superannotate import SAClient
sa = SAClient()
from tests.integration.base import BaseTestCase


class TestGetAnnotations(BaseTestCase):
    PROJECT_NAME = "Test-get_annotations"
    FOLDER_NAME = "Test-get_annotations"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    IMAGE_NAME = "example_image_1.jpg"

    @property
    def folder_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.TEST_FOLDER_PATH)

    # @pytest.mark.flaky(reruns=3)
    def test_get_annotations(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        _, _, _ = sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path
        )

        annotations = sa.get_annotations(f"{self.PROJECT_NAME}", [self.IMAGE_NAME])
        self.assertEqual(len(annotations), 1)
        with open(f"{self.folder_path}/{self.IMAGE_NAME}___objects.json", "r") as annotation_file:
            annotation_data = json.load(annotation_file)
            self.assertEqual(len(annotation_data["instances"]), len(annotations[0]["instances"]))
        parse_obj_as(List[VectorAnnotation], annotations)

    @pytest.mark.flaky(reruns=3)
    def test_get_annotations_order(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        _, _, _ = sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path
        )
        names = [
            self.IMAGE_NAME, self.IMAGE_NAME.replace("1", "2"),
            self.IMAGE_NAME.replace("1", "3"), self.IMAGE_NAME.replace("1", "4")
        ]
        annotations = sa.get_annotations(f"{self.PROJECT_NAME}", names)
        self.assertEqual(names, [i["metadata"]["name"] for i in annotations])

    @pytest.mark.flaky(reruns=3)
    def test_get_annotations_from_folder(self):
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_NAME)

        sa.upload_images_from_folder_to_project(
            f"{self.PROJECT_NAME}/{self.FOLDER_NAME}", self.folder_path, annotation_status="InProgress"
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        _, _, _ = sa.upload_annotations_from_folder_to_project(
            f"{self.PROJECT_NAME}/{self.FOLDER_NAME}", self.folder_path
        )

        annotations = sa.get_annotations(f"{self.PROJECT_NAME}/{self.FOLDER_NAME}", [self.IMAGE_NAME])
        self.assertEqual(len(annotations), 1)
        with open(f"{self.folder_path}/{self.IMAGE_NAME}___objects.json", "r") as annotation_file:
            annotation_data = json.load(annotation_file)
            self.assertEqual(len(annotation_data["instances"]), len(annotations[0]["instances"]))
        parse_obj_as(List[VectorAnnotation], annotations)

    @pytest.mark.flaky(reruns=3)
    def test_get_annotations_all(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        _, _, _ = sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path
        )
        annotations = sa.get_annotations(f"{self.PROJECT_NAME}")
        self.assertEqual(len(annotations), 4)

    @pytest.mark.flaky(reruns=3)
    def test_get_annotations_all_plus_folder(self):
        sa.create_folder(self.PROJECT_NAME, self.FOLDER_NAME)
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        sa.upload_images_from_folder_to_project(
            f"{self.PROJECT_NAME}/{self.FOLDER_NAME}", self.folder_path, annotation_status="InProgress"
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )
        _, _, _ = sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path
        )
        annotations = sa.get_annotations(f"{self.PROJECT_NAME}")
        self.assertEqual(len(annotations), 4)


class TestGetAnnotationsVideo(BaseTestCase):
    PROJECT_NAME = "test attach multiple video urls"
    PATH_TO_URLS = "data_set/video_urls.csv"
    PATH_TO_URLS_WITHOUT_NAMES = "data_set/attach_urls_with_no_name.csv"
    PATH_TO_50K_URLS = "data_set/501_urls.csv"
    PROJECT_DESCRIPTION = "desc"
    ANNOTATIONS_PATH = "data_set/video_annotations"
    VIDEO_NAME = "video.mp4"
    CLASSES_PATH = "data_set/video_annotation/classes/classes.json"
    PROJECT_TYPE = "Video"

    @property
    def csv_path(self):
        return os.path.join(dirname(dirname(dirname(__file__))), self.PATH_TO_URLS)

    @property
    def classes_path(self):
        return os.path.join(self.folder_path, self.CLASSES_PATH)

    @property
    def folder_path(self):
        return Path(__file__).parent.parent.parent

    @property
    def annotations_path(self):
        return os.path.join(self.folder_path, self.ANNOTATIONS_PATH)

    def test_video_annotation_upload_root(self):
        sa.create_annotation_classes_from_classes_json(self.PROJECT_NAME, self.classes_path)

        _, _, _ = sa.attach_items(
            self.PROJECT_NAME,
            self.csv_path,
        )
        sa.upload_annotations_from_folder_to_project(self.PROJECT_NAME, self.annotations_path)
        annotations = sa.get_annotations(self.PROJECT_NAME)
        self.assertEqual(len(annotations), 2)

    def test_video_annotation_upload_folder(self):
        sa.create_annotation_classes_from_classes_json(self.PROJECT_NAME, self.classes_path)
        sa.create_folder(self.PROJECT_NAME, "folder")
        path = f"{self.PROJECT_NAME}/folder"
        _, _, _ = sa.attach_items(
            path,
            self.csv_path,
        )
        sa.upload_annotations_from_folder_to_project(path, self.annotations_path)
        annotations = sa.get_annotations(path)
        self.assertEqual(len(annotations), 2)
