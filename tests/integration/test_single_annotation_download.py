import filecmp
import json
import os
import tempfile
from os.path import dirname
import pytest

import src.superannotate as sa
from tests.integration.base import BaseTestCase


class TestSingleAnnotationDownloadUpload(BaseTestCase):
    PROJECT_NAME = "test_single_annotation"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PTH = "data_set"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    @property
    def classes_path(self):
        return os.path.join(
            dirname(dirname(__file__)), self.TEST_FOLDER_PATH, "classes/classes.json"
        )


    # TODO: template name validation error
    def test_annotation_download_upload_vector(self):
        sa.upload_images_from_folder_to_project(
            project=self.PROJECT_NAME, folder_path=self.folder_path
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.classes_path
        )
        sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path
        )
        image = sa.search_images(self.PROJECT_NAME)[0]

        tempdir = tempfile.TemporaryDirectory()
        paths = sa.download_image_annotations(self.PROJECT_NAME, image, tempdir.name)
        downloaded_json = json.load(open(paths[0]))

        uploaded_json = json.load(
            open(self.folder_path + "/example_image_1.jpg___objects.json")
        )
        downloaded_json['metadata']['lastAction'] = None
        uploaded_json['metadata']['lastAction'] = None

        for i in downloaded_json["instances"]:
            i.pop("classId", None)
            for j in i["attributes"]:
                j.pop("groupId", None)
                j.pop("id", None)
        for i in uploaded_json["instances"]:
            i.pop("classId", None)
            for j in i["attributes"]:
                j.pop("groupId", None)
                j.pop("id", None)
        self.assertTrue(
            all(
                [instance["templateId"] == -1 for instance in downloaded_json["instances"] if
                 instance.get("templateId")]
            )
        )
        # TODO:
        #assert downloaded_json == uploaded_json


class TestSingleAnnotationDownloadUploadPixel(BaseTestCase):
    PROJECT_NAME = "test_single_annotation_pixel"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Pixel"
    TEST_FOLDER_PTH = "data_set"
    TEST_FOLDER_PATH = "data_set/sample_project_pixel"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    @property
    def classes_path(self):
        return os.path.join(
            dirname(dirname(__file__)), self.TEST_FOLDER_PATH, "classes/classes.json"
        )

    @pytest.mark.flaky(reruns=2)
    def test_annotation_download_upload_pixel(self):
        sa.upload_images_from_folder_to_project(
            project=self.PROJECT_NAME, folder_path=self.folder_path
        )
        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, self.classes_path
        )
        sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path
        )
        image = sa.search_images(self.PROJECT_NAME)[0]

        with tempfile.TemporaryDirectory() as tempdir:
            paths = sa.download_image_annotations(self.PROJECT_NAME, image, tempdir)
            downloaded_json = json.load(open(paths[0]))
            uploaded_json = json.load(
                open(self.folder_path + "/example_image_1.jpg___pixel.json")
            )
            downloaded_json['metadata']['lastAction'] = None
            uploaded_json['metadata']['lastAction'] = None
            for i in downloaded_json["instances"]:
                i.pop("classId", None)
                for j in i["attributes"]:
                    j.pop("groupId", None)
                    j.pop("id", None)
            for i in uploaded_json["instances"]:
                i.pop("classId", None)
                for j in i["attributes"]:
                    j.pop("groupId", None)
                    j.pop("id", None)
            assert downloaded_json == uploaded_json

            uploaded_mask = self.folder_path + "/example_image_1.jpg___save.png"
            download_mask = paths[1]
            assert filecmp.cmp(download_mask, uploaded_mask, shallow=False)
