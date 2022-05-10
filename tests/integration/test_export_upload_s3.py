import os
import tempfile
from os.path import dirname

import boto3
from src.superannotate import SAClient
sa = SAClient()
from tests.integration.base import BaseTestCase


class TestExportUploadS3(BaseTestCase):
    PROJECT_NAME = "export_upload_s3"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PTH = "data_set"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    TEST_S3_BUCKET = "superannotate-python-sdk-test"
    S3_PREFIX2 = "frex_temp"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    def test_export_upload(self):
        sa.upload_images_from_folder_to_project(
            project=self.PROJECT_NAME,
            folder_path=self.folder_path,
            annotation_status="QualityCheck",
        )
        s3_client = boto3.client("s3")
        paginator = s3_client.get_paginator("list_objects_v2")

        files = []

        with tempfile.TemporaryDirectory() as temp_dir:
            download_location = temp_dir
            response_iterator = paginator.paginate(
                Bucket=self.TEST_S3_BUCKET, Prefix=self.S3_PREFIX2
            )
            for response in response_iterator:
                if "Contents" in response:
                    for object_data in response["Contents"]:
                        key = object_data["Key"]
                        s3_client.delete_object(Bucket=self.TEST_S3_BUCKET, Key=key)
            new_export = sa.prepare_export(self.PROJECT_NAME, include_fuse=True)
            sa.download_export(
                self.PROJECT_NAME,
                new_export,
                download_location,
                to_s3_bucket=self.TEST_S3_BUCKET,
            )
            response_iterator = paginator.paginate(
                Bucket=self.TEST_S3_BUCKET, Prefix=download_location
            )
            for response in response_iterator:
                if "Contents" in response:
                    for object_data in response["Contents"]:
                        key = object_data["Key"]
                        files.append(key)

        with tempfile.TemporaryDirectory() as temp_dir:

            output_path = temp_dir
            sa.download_export(self.PROJECT_NAME, new_export, output_path)
            local_files = os.listdir(output_path)

            self.assertEqual(len(local_files), len(files))
