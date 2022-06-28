import os
import tempfile
import json
from pathlib import Path
import pytest
from src.superannotate import SAClient
sa = SAClient()
from tests.integration.base import BaseTestCase


class TestUploadTextAnnotation(BaseTestCase):
    PROJECT_NAME = "text annotation upload"
    PATH_TO_URLS = "data_set/csv_files/text_urls_template.csv"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Document"
    ANNOTATIONS_PATH = "data_set/document_annotation"
    CLASSES_PATH = "data_set/document_annotation/classes/classes.json"
    ANNOTATIONS_PATH_INVALID_JSON = "data_set/document_annotation_invalid_json"
    ANNOTATIONS_PATH_WITHOUT_CLASS_DATA = "data_set/document_annotation_without_class_data"

    @property
    def folder_path(self):
        return Path(__file__).parent.parent.parent

    @property
    def csv_path(self):
        return os.path.join(self.folder_path, self.PATH_TO_URLS)

    @property
    def annotations_path(self):
        return os.path.join(self.folder_path, self.ANNOTATIONS_PATH)

    @property
    def annotations_path_without_class_data(self):
        return os.path.join(self.folder_path, self.ANNOTATIONS_PATH_WITHOUT_CLASS_DATA)

    @property
    def invalid_annotations_path(self):
        return os.path.join(self.folder_path, self.ANNOTATIONS_PATH_INVALID_JSON)

    @property
    def classes_path(self):
        return os.path.join(self.folder_path, self.CLASSES_PATH)

    @pytest.fixture(autouse=True)
    def inject_fixtures(self, caplog):
        self._caplog = caplog

    def test_document_annotation_upload_invalid_json(self):
        sa.create_annotation_classes_from_classes_json(self.PROJECT_NAME, self.classes_path)

        _, _, _ = sa.attach_items(
            self.PROJECT_NAME,
            self.csv_path,
        )
        (uploaded_annotations, failed_annotations, missing_annotations) = sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.invalid_annotations_path)
        self.assertEqual(len(uploaded_annotations), 0)
        self.assertEqual(len(failed_annotations), 1)
        self.assertEqual(len(missing_annotations), 0)
        self.assertIn("Couldn't validate 1/1 annotations", self._caplog.text)
        self.assertIn("Use the validate_annotations function to discover the possible reason(s) for which an annotation is invalid.", self._caplog.text)

    def test_text_annotation_upload(self):
        sa.create_annotation_classes_from_classes_json(self.PROJECT_NAME, self.classes_path)

        _, _, _ = sa.attach_items(
            self.PROJECT_NAME,
            self.csv_path,
        )
        sa.upload_annotations_from_folder_to_project(self.PROJECT_NAME, self.annotations_path)
        export = sa.prepare_export(self.PROJECT_NAME)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = temp_dir
            sa.download_export(self.PROJECT_NAME, export, output_path, True)
            classes = sa.search_annotation_classes(self.PROJECT_NAME)
            downloaded_annotation = json.loads(open(f"{output_path}/text_file_example_1.json").read())
            instance = downloaded_annotation['instances'][0]
            self.assertEqual(instance['classId'], classes[0]['id'])
            self.assertEqual(downloaded_annotation['tags'][0], "vid")

    def test_document_annotation_without_class_data(self):
        sa.create_annotation_classes_from_classes_json(self.PROJECT_NAME, self.classes_path)
        _, _, _ = sa.attach_items(
            self.PROJECT_NAME,
            self.csv_path,
        )
        sa.upload_annotations_from_folder_to_project(self.PROJECT_NAME, self.annotations_path_without_class_data)
        export = sa.prepare_export(self.PROJECT_NAME)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = temp_dir
            sa.download_export(self.PROJECT_NAME, export, output_path, True)
            downloaded_annotation = json.loads(open(f"{output_path}/text_file_example_1.json").read())
            instance = downloaded_annotation['instances'][0]
            self.assertEqual(instance['classId'], -1)
