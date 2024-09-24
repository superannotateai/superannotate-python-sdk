import filecmp
import json
import logging
import os
import tempfile
from unittest import TestCase

import boto3
from src.superannotate import AppException
from src.superannotate import SAClient
from tests import compare_result
from tests.integration.export import DATA_SET_PATH

sa = SAClient()
s3_client = boto3.client("s3")


class TestExportImport(TestCase):
    PROJECT_NAME = "export_import"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    FOLDER_NAME = "folder"
    TEST_S3_BUCKET = "superannotate-python-sdk-test"
    TEST_FOLDER_PATH = os.path.join(DATA_SET_PATH, "sample_project_vector")
    CLASSES_PATH = os.path.join(TEST_FOLDER_PATH, "classes/classes.json")
    TMP_DIR = "TMP_DIR"
    IGNORE_KEYS = {
        "id",
        "team_id",
        "createdAt",
        "updatedAt",
        "project_id",
        "projectId",
        "isPredicted",
        "lastAction",
    }

    @classmethod
    def setUpClass(cls) -> None:
        cls.tearDownClass()
        cls._project = sa.create_project(
            cls.PROJECT_NAME, cls.PROJECT_DESCRIPTION, cls.PROJECT_TYPE
        )  # noqa
        cls.folder = sa.create_folder(
            project=cls.PROJECT_NAME, folder_name=cls.FOLDER_NAME
        )
        sa.create_annotation_classes_from_classes_json(
            cls.PROJECT_NAME, cls.CLASSES_PATH
        )

        sa.upload_images_from_folder_to_project(cls.PROJECT_NAME, cls.TEST_FOLDER_PATH)
        sa.upload_annotations_from_folder_to_project(
            cls.PROJECT_NAME, cls.TEST_FOLDER_PATH, recursive_subfolders=True
        )

        sa.upload_images_from_folder_to_project(
            f"{cls.PROJECT_NAME}/{cls.FOLDER_NAME}", cls.TEST_FOLDER_PATH
        )
        sa.upload_annotations_from_folder_to_project(
            f"{cls.PROJECT_NAME}/{cls.FOLDER_NAME}",
            os.path.join(cls.TEST_FOLDER_PATH, cls.FOLDER_NAME),
        )

    @classmethod
    def tearDownClass(cls) -> None:
        projects = sa.search_projects(cls.PROJECT_NAME, return_metadata=True)
        for project in projects:
            try:
                sa.delete_project(project)
            except AppException as e:
                logging.error(e)

    def test_export_import(self):
        with tempfile.TemporaryDirectory() as tmpdir_name:
            export = sa.prepare_export(self.PROJECT_NAME, include_fuse=True)
            sa.download_export(self.PROJECT_NAME, export, tmpdir_name)
            assert not filecmp.dircmp(tmpdir_name, self.TEST_FOLDER_PATH).left_only
            assert not filecmp.dircmp(tmpdir_name, self.TEST_FOLDER_PATH).right_only
            for path, sub_dirs, files in os.walk(tmpdir_name):
                for name in files:
                    if not name.endswith(".json"):
                        continue
                    folder_name = path.split(tmpdir_name)[-1]
                    folder_name = folder_name.replace("/", "")
                    if folder_name == "classes":
                        continue
                    with open(os.path.join(path, name), encoding="utf-8") as f:
                        actual = json.load(f)
                    with open(
                        os.path.join(self.TEST_FOLDER_PATH, folder_name, name),
                        encoding="utf-8",
                    ) as f:
                        expected = json.load(f)

                    assert compare_result(
                        actual, expected, ignore_keys=self.IGNORE_KEYS
                    )

    def test_upload_s3(self):
        files = []
        new_export = sa.prepare_export(self.PROJECT_NAME, include_fuse=True)
        sa.download_export(
            project=self.PROJECT_NAME,
            export=new_export,
            folder_path=self.TMP_DIR,
            to_s3_bucket=self.TEST_S3_BUCKET,
            extract_zip_contents=True,
        )
        for object_data in s3_client.list_objects_v2(
            Bucket=self.TEST_S3_BUCKET, Prefix=self.TMP_DIR
        ).get("Contents", []):
            files.append(object_data["Key"])
        self.assertEqual(25, len(files))

    def test_export_with_statuses(self):
        with tempfile.TemporaryDirectory() as tmpdir_name:
            export = sa.prepare_export(self.PROJECT_NAME, annotation_statuses=['NotStarted', 'InProgress'], include_fuse=True)
            sa.download_export(self.PROJECT_NAME, export, tmpdir_name)
            assert not filecmp.dircmp(tmpdir_name, self.TEST_FOLDER_PATH).left_only
            assert  filecmp.dircmp(tmpdir_name, self.TEST_FOLDER_PATH).right_only