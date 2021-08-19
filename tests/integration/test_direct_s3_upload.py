from pathlib import Path

import boto3
import src.superannotate as sa
from tests.integration.base import BaseTestCase


class TestDirectS3Upload(BaseTestCase):
    PROJECT_NAME = "test_direct_s3_upload"
    TEST_FOLDER_NAME = "test_folder"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"
    S3_BUCKET = "superannotate-python-sdk-test"
    S3_FOLDER = "sample_project_vector"

    def test_direct_s3_upload(self):
        csv = (Path.home() / ".aws" / "credentials").read_text().splitlines()
        access_key_id = csv[1].split("=")[1].strip()
        access_secret = csv[2].split("=")[1].strip()

        sa.upload_images_from_s3_bucket_to_project(
            self.PROJECT_NAME,
            access_key_id,
            access_secret,
            self.S3_BUCKET,
            self.S3_FOLDER,
        )
        s3_client = boto3.client("s3")
        paginator = s3_client.get_paginator("list_objects_v2")
        response_iterator = paginator.paginate(
            Bucket=self.S3_BUCKET, Prefix=self.S3_FOLDER
        )
        on_s3 = []
        for response in response_iterator:
            if "Contents" in response:
                for object_data in response["Contents"]:
                    key = object_data["Key"]
                    if key[-4:] in [".jpg", ".png"]:
                        on_s3.append(key)

        self.assertEqual(len(on_s3), sa.get_project_image_count(self.PROJECT_NAME))

    def test_direct_s3_upload_folder(self):
        csv = (Path.home() / ".aws" / "credentials").read_text().splitlines()
        access_key_id = csv[1].split("=")[1].strip()
        access_secret = csv[2].split("=")[1].strip()

        sa.create_folder(self.PROJECT_NAME, self.TEST_FOLDER_NAME)
        project_folder = f"{self.PROJECT_NAME}/{self.TEST_FOLDER_NAME}"

        sa.upload_images_from_s3_bucket_to_project(
            project_folder, access_key_id, access_secret, self.S3_BUCKET, self.S3_FOLDER
        )
        s3_client = boto3.client("s3")
        paginator = s3_client.get_paginator("list_objects_v2")
        response_iterator = paginator.paginate(
            Bucket=self.S3_BUCKET, Prefix=self.S3_FOLDER
        )
        on_s3 = []
        for response in response_iterator:
            if "Contents" in response:
                for object_data in response["Contents"]:
                    key = object_data["Key"]
                    if key[-4:] in [".jpg", ".png"]:
                        on_s3.append(key)

        self.assertEqual(len(on_s3), len(sa.search_images(project_folder)))
