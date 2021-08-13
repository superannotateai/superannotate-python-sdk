import json
import os
import tempfile
import time
from os.path import dirname
from pathlib import Path

import src.lib.app.superannotate as sa
from src.tests.integration.base import BaseTestCase


class TestProjectSettings(BaseTestCase):
    PROJECT_NAME = "test_recursive"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PATH = "data_set/sample_recursive_test"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    def test_non_recursive_annotations_folder(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME,
            self.folder_path,
            annotation_status="QualityCheck",
            recursive_subfolders=True,
        )
        time.sleep(2)
        self.assertEqual(len(sa.search_images(self.PROJECT_NAME)), 2)

        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )

        sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, recursive_subfolders=False
        )

        export = sa.prepare_export(self.PROJECT_NAME)

        time.sleep(2)
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

        self.assertEqual(len(sa.search_images(self.PROJECT_NAME)), 2)

        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )

        sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, recursive_subfolders=True
        )

        export = sa.prepare_export(self.PROJECT_NAME)

        time.sleep(1)
        with tempfile.TemporaryDirectory() as tmp_dir:
            sa.download_export(self.PROJECT_NAME, export["name"], tmp_dir)
            self.assertEqual(len(list(Path(tmp_dir).glob("*.json"))), 2)

    def test_recursive_pre_annotations_folder(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME,
            self.folder_path,
            annotation_status="QualityCheck",
            recursive_subfolders=True,
        )

        self.assertEqual(len(sa.search_images(self.PROJECT_NAME)), 2)

        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )

        sa.upload_preannotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, recursive_subfolders=True
        )

        time.sleep(2)
        with tempfile.TemporaryDirectory() as tmp_dir:
            for image in sa.search_images(self.PROJECT_NAME):
                sa.download_image_preannotations(self.PROJECT_NAME, image, tmp_dir)

            self.assertEqual(len(list(Path(tmp_dir).glob("*.json"))), 2)

    def test_non_recursive_pre_annotations_folder(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME,
            self.folder_path,
            annotation_status="QualityCheck",
            recursive_subfolders=True,
        )

        self.assertEqual(len(sa.search_images(self.PROJECT_NAME)), 2)

        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME, f"{self.folder_path}/classes/classes.json"
        )

        sa.upload_preannotations_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, recursive_subfolders=True
        )

        time.sleep(2)
        with tempfile.TemporaryDirectory() as tmp_dir:
            for image in sa.search_images(self.PROJECT_NAME):
                sa.download_image_preannotations(self.PROJECT_NAME, image, tmp_dir)

            self.assertEqual(len(list(Path(tmp_dir).glob("*.json"))), 2)

    def test_annotations_recursive_s3_folder(self):

        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME,
            self.folder_path,
            annotation_status="QualityCheck",
            from_s3_bucket="superannotate-python-sdk-test",
            recursive_subfolders=True,
        )
        self.assertEqual(len(sa.search_images(self.PROJECT_NAME)), 2)

        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME,
            f"{self.folder_path}/classes/classes.json",
            from_s3_bucket="superannotate-python-sdk-test",
        )

        sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME,
            self.folder_path,
            recursive_subfolders=True,
            from_s3_bucket="superannotate-python-sdk-test",
        )
        time.sleep(2)

        export = sa.prepare_export(self.PROJECT_NAME)

        time.sleep(2)
        with tempfile.TemporaryDirectory() as tmp_dir:
            sa.download_export(self.PROJECT_NAME, export["name"], tmp_dir)

            self.assertEqual(len(list(Path(tmp_dir).glob("*.json"))), 2)

    def test_annotations_non_recursive_s3_folder(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME,
            self.folder_path,
            annotation_status="QualityCheck",
            from_s3_bucket="superannotate-python-sdk-test",
            recursive_subfolders=True,
        )

        self.assertEqual(len(sa.search_images(self.PROJECT_NAME)), 2)

        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME,
            f"{self.folder_path}/classes/classes.json",
            from_s3_bucket="superannotate-python-sdk-test",
        )

        sa.upload_annotations_from_folder_to_project(
            self.PROJECT_NAME,
            self.folder_path,
            recursive_subfolders=False,
            from_s3_bucket="superannotate-python-sdk-test",
        )

        export = sa.prepare_export(self.PROJECT_NAME)

        time.sleep(1)
        with tempfile.TemporaryDirectory() as tmp_dir:
            sa.download_export(self.PROJECT_NAME, export["name"], tmp_dir)
            non_empty_annotations = 0
            json_files = Path(tmp_dir).glob("*.json")
            for json_file in json_files:
                json_ann = json.load(open(json_file))
                if "instances" in json_ann and len(json_ann["instances"]) > 0:
                    non_empty_annotations += 1

            self.assertEqual(non_empty_annotations, 1)

    def test_pre_annotations_recursive_s3_folder(self):

        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME,
            self.folder_path,
            from_s3_bucket="superannotate-python-sdk-test",
            recursive_subfolders=True,
        )
        time.sleep(2)

        self.assertEqual(len(sa.search_images(self.PROJECT_NAME)), 2)

        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME,
            f"{self.folder_path}/classes/classes.json",
            from_s3_bucket="superannotate-python-sdk-test",
        )

        sa.upload_preannotations_from_folder_to_project(
            self.PROJECT_NAME,
            self.folder_path,
            recursive_subfolders=True,
            from_s3_bucket="superannotate-python-sdk-test",
        )
        time.sleep(2)
        with tempfile.TemporaryDirectory() as tmp_dir:
            for image in sa.search_images(self.PROJECT_NAME):
                sa.download_image_preannotations(self.PROJECT_NAME, image, tmp_dir)

            self.assertEqual(len(list(Path(tmp_dir).glob("*.json"))), 2)

    def test_pre_annotations_non_recursive_s3_folder(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME,
            self.folder_path,
            from_s3_bucket="superannotate-python-sdk-test",
            recursive_subfolders=True,
        )
        time.sleep(2)

        self.assertEqual(len(sa.search_images(self.PROJECT_NAME)), 2)

        sa.create_annotation_classes_from_classes_json(
            self.PROJECT_NAME,
            f"{self.PROJECT_NAME}/classes/classes.json",
            from_s3_bucket="superannotate-python-sdk-test",
        )

        sa.upload_preannotations_from_folder_to_project(
            self.PROJECT_NAME,
            self.folder_path,
            recursive_subfolders=False,
            from_s3_bucket="superannotate-python-sdk-test",
        )
        time.sleep(2)
        with tempfile.TemporaryDirectory() as tmp_dir:
            for image in sa.search_images(self.PROJECT_NAME):
                sa.download_image_preannotations(self.PROJECT_NAME, image, tmp_dir)

    def test_images_non_recursive_s3(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME,
            self.folder_path,
            from_s3_bucket="superannotate-python-sdk-test",
            recursive_subfolders=False,
        )
        time.sleep(2)

        self.assertEqual(len(sa.search_images(self.PROJECT_NAME)), 1)

    def test_images_non_recursive(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, recursive_subfolders=False
        )
        time.sleep(2)
        self.assertEqual(len(sa.search_images(self.PROJECT_NAME)), 1)
