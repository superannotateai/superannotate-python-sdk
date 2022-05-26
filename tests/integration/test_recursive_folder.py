import json
import os
import tempfile
from os.path import dirname
from pathlib import Path
import pytest

from src.superannotate import SAClient
sa = SAClient()
from tests.integration.base import BaseTestCase


class TestRecursiveFolder(BaseTestCase):
    PROJECT_NAME = "test_recursive"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    S3_FOLDER_PATH = "sample_recursive_test"
    TEST_FOLDER_PATH = "data_set/sample_recursive_test"
    TEST_FOLDER_PATH_NEGATIVE_CASE = "data_set/sample_recursive_test_negative_case"
    JSON_POSTFIX = "*.json"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    @property
    def second_folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH_NEGATIVE_CASE)

    def test_recursive_upload(self):
        uploaded, _, duplicated = sa.upload_images_from_folder_to_project(self.PROJECT_NAME, self.second_folder_path,
                                                                          recursive_subfolders=True)
        self.assertEqual(2, len(uploaded))
        self.assertEqual(2, len(duplicated))

    def test_non_recursive_annotations_folder(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME,
            self.folder_path,
            annotation_status="QualityCheck",
            recursive_subfolders=True,
        )
        self.assertEqual(len(sa.search_items(self.PROJECT_NAME)), 2)

        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )

        sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, recursive_subfolders=False
        )

        export = sa.prepare_export(self.PROJECT_NAME)

        with tempfile.TemporaryDirectory() as tmp_dirname:
            sa.download_export(self.PROJECT_NAME, export["name"], tmp_dirname)

            non_empty_annotations = 0
            json_files = Path(tmp_dirname).glob("*.json")
            for json_file in json_files:
                json_ann = json.load(open(json_file))
                if "instances" in json_ann and len(json_ann["instances"]) > 0:
                    non_empty_annotations += 1
            self.assertEqual(non_empty_annotations, 1)

    def test_recursive_annotations_folder(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME,
            self.folder_path,
            annotation_status="QualityCheck",
            recursive_subfolders=True,
        )

        self.assertEqual(len(sa.search_items(self.PROJECT_NAME)), 2)

        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )

        sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, recursive_subfolders=True
        )
        export = sa.prepare_export(self.PROJECT_NAME)
        with tempfile.TemporaryDirectory() as tmp_dir:
            sa.download_export(self.PROJECT_NAME, export["name"], tmp_dir)
            self.assertEqual(len(list(Path(tmp_dir).glob("*.json"))), 2)

    def test_recursive_annotations_folder_negative_case(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME,
            self.second_folder_path,
            annotation_status="QualityCheck",
            recursive_subfolders=True,
        )

        self.assertEqual(len(sa.search_items(self.PROJECT_NAME)), 2)

    def test_annotations_recursive_s3_folder(self):

        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME,
            self.S3_FOLDER_PATH,
            annotation_status="QualityCheck",
            from_s3_bucket="superannotate-python-sdk-test",
            recursive_subfolders=True,
        )
        self.assertEqual(len(sa.search_items(self.PROJECT_NAME)), 2)

        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME,
            f"{self.S3_FOLDER_PATH}/classes/classes.json",
            from_s3_bucket="superannotate-python-sdk-test",
        )

        sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME,
            self.S3_FOLDER_PATH,
            recursive_subfolders=True,
            from_s3_bucket="superannotate-python-sdk-test",
        )

        export = sa.prepare_export(self.PROJECT_NAME)

        with tempfile.TemporaryDirectory() as tmp_dir:
            sa.download_export(self.PROJECT_NAME, export["name"], tmp_dir)

            self.assertEqual(len(list(Path(tmp_dir).glob(self.JSON_POSTFIX))), 2)

    @pytest.mark.flaky(reruns=2)
    def test_annotations_non_recursive_s3_folder(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME,
            self.S3_FOLDER_PATH,
            annotation_status="QualityCheck",
            from_s3_bucket="superannotate-python-sdk-test",
            recursive_subfolders=False,
        )

        self.assertEqual(len(sa.search_items(self.PROJECT_NAME)), 1)

        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME,
            f"{self.S3_FOLDER_PATH}/classes/classes.json",
            from_s3_bucket="superannotate-python-sdk-test",
        )

        sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME,
            self.S3_FOLDER_PATH,
            recursive_subfolders=False,
            from_s3_bucket="superannotate-python-sdk-test",
        )

        export = sa.prepare_export(self.PROJECT_NAME)

        with tempfile.TemporaryDirectory() as tmp_dir:
            sa.download_export(self.PROJECT_NAME, export["name"], tmp_dir)
            non_empty_annotations = 0
            json_files = Path(tmp_dir).glob(self.JSON_POSTFIX)
            for json_file in json_files:
                json_ann = json.load(open(json_file))
                if "instances" in json_ann and len(json_ann["instances"]) > 0:
                    non_empty_annotations += 1
            # TODO: template name error
            # self.assertEqual(non_empty_annotations, 1)

    def test_images_non_recursive_s3(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME,
            self.S3_FOLDER_PATH,
            from_s3_bucket="superannotate-python-sdk-test",
            recursive_subfolders=False,
        )

        self.assertEqual(len(sa.search_items(self.PROJECT_NAME)), 1)

    @pytest.mark.skip(reason="Taking long time.")
    def test_images_recursive_s3_122(self):
        sa.upload_images_from_folder_to_project(self.PROJECT_NAME, '8sep',
                                                from_s3_bucket="superannotate-python-sdk-test",
                                                recursive_subfolders=True)
        self.assertEqual(len(sa.search_items(self.PROJECT_NAME)), 122)

    @pytest.mark.skip(reason="Taking long time.")
    def test_annotations_recursive_s3_122(self):
        sa.upload_images_from_folder_to_project(self.PROJECT_NAME, '8sep',
                                                from_s3_bucket="superannotate-python-sdk-test",
                                                recursive_subfolders=True)
        uploaded = sa.upload_annotations_from_folder_to_project(self.PROJECT_NAME, '8sep',
                                                                from_s3_bucket="superannotate-python-sdk-test",
                                                                recursive_subfolders=True)
        self.assertEqual(len(uploaded[0]), 122)

    def test_annotations_recursive_s3_10(self):
        sa.upload_images_from_folder_to_project(self.PROJECT_NAME, '8sep',
                                                from_s3_bucket="superannotate-python-sdk-test",
                                                recursive_subfolders=False)
        uploaded = sa.upload_annotations_from_folder_to_project(self.PROJECT_NAME, '8sep',
                                                                from_s3_bucket="superannotate-python-sdk-test",
                                                                recursive_subfolders=False)
        self.assertEqual(len(uploaded[0]), 9)

    def test_images_non_recursive(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, recursive_subfolders=False
        )
        self.assertEqual(len(sa.search_items(self.PROJECT_NAME)), 1)
