import os
import tempfile
from os.path import dirname

import boto3

import src.superannotate as sa
from src.superannotate import SAClient
from tests.integration.base import BaseTestCase


sa = SAClient()

s3_client = boto3.client("s3")


class TestExportUploadS3(BaseTestCase):
    PROJECT_NAME = "export_upload_s3"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PTH = "data_set"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    TEST_S3_BUCKET = "superannotate-python-sdk-test"
    TMP_DIR = "TMP_DIR"

    def tearDown(self) -> None:
        super().tearDown()
        for object_data in s3_client.list_objects_v2(Bucket=self.TEST_S3_BUCKET, Prefix=self.TMP_DIR).get("Contents",
                                                                                                          []):
            s3_client.delete_object(Bucket=self.TEST_S3_BUCKET, Key=object_data["Key"])

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    def test_export_upload(self):
        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_PTH)
        sa.upload_images_from_folder_to_project(
            project=f"{self.PROJECT_NAME}/{self.TEST_FOLDER_PTH}",
            folder_path=self.folder_path,
            annotation_status="QualityCheck",
        )

        files = []
        new_export = sa.prepare_export(self.PROJECT_NAME, include_fuse=True)
        sa.download_export(
            project=self.PROJECT_NAME,
            export=new_export,
            folder_path=self.TMP_DIR,
            to_s3_bucket=self.TEST_S3_BUCKET,
            extract_zip_contents=True
        )
        for object_data in s3_client.list_objects_v2(Bucket=self.TEST_S3_BUCKET, Prefix=self.TMP_DIR).get("Contents",
                                                                                                          []):
            files.append(object_data["Key"])
        self.assertEqual(13, len(files))
