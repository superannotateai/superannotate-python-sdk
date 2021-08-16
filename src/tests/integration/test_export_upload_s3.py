import os
import tempfile
from os.path import dirname

import boto3
import src.lib.app.superannotate as sa
from src.tests.integration.base import BaseTestCase


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
        # sa.upload_images_from_folder_to_project(
        #     project=self.PROJECT_NAME, folder_path=self.folder_path,annotation_status="QualityCheck"
        # )
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

            assert len(local_files) == len(files)


# import time
# from pathlib import Path
#
# import boto3
#
# import superannotate as sa
# from .test_assign_images import safe_create_project
#
# from .common import upload_project
# s3_client = boto3.client('s3')
#
# S3_PREFIX = 'frex9'
# S3_PREFIX2 = 'frex_temp'
# S3_BUCKET = 'superannotate-python-sdk-test'
# PROJECT_NAME_EXPORT = "Example project test export upload s3 export "
# PROJECT_NAME_UPLOAD = "Example project test export upload s3 upload"
#
#
#
# def test_export_s3(tmpdir):
#     paginator = s3_client.get_paginator('list_objects_v2')
#     response_iterator = paginator.paginate(Bucket=S3_BUCKET, Prefix=S3_PREFIX2)
#     for response in response_iterator:
#         if 'Contents' in response:
#             for object_data in response['Contents']:
#                 key = object_data['Key']
#                 s3_client.delete_object(Bucket=S3_BUCKET, Key=key)
#     tmpdir = Path(tmpdir)
#
#     project = upload_project(
#         Path("./tests/sample_project_vector"),
#         PROJECT_NAME_EXPORT,
#         'test',
#         'Vector',
#         annotation_status='InProgress'
#     )
#     # projects = sa.search_projects(PROJECT_NAME_EXPORT, return_metadata=True)
#     # for project in projects:
#     #     sa.delete_project(project)
#     # project = sa.create_project(PROJECT_NAME_EXPORT, "test", "Vector")
#
#     # sa.upload_images_from_folder_to_project(
#     #     project,
#     #     Path("./tests/sample_project_vector"),
#     #     annotation_status="InProgress"
#     # )
#     # sa.create_annotation_classes_from_classes_json(
#     #     project, Path("./tests/sample_project_vector/classes/classes.json")
#     # )
#     # sa.upload_annotations_from_folder_to_project(
#     #     project, Path("./tests/sample_project_vector")
#     # )
#     images = sa.search_images(project)
#     for img in images:
#         sa.set_image_annotation_status(project, img, 'QualityCheck')
#
#     new_export = sa.prepare_export(project, include_fuse=True)
#     sa.download_export(project, new_export, S3_PREFIX2, to_s3_bucket=S3_BUCKET)
#
#     files = []
#     response_iterator = paginator.paginate(Bucket=S3_BUCKET, Prefix=S3_PREFIX2)
#     for response in response_iterator:
#         if 'Contents' in response:
#             for object_data in response['Contents']:
#                 key = object_data['Key']
#                 files.append(key)
#     output_path = tmpdir / S3_PREFIX2
#     output_path.mkdir()
#     sa.download_export(project, new_export, output_path)
#     local_files = list(output_path.rglob("*.*"))
#
#     assert len(local_files) == len(files)
#
#
# def test_from_s3_upload():
#     project = safe_create_project(PROJECT_NAME_UPLOAD, "hk", "Vector")
#     sa.create_annotation_classes_from_classes_json(
#         project, "frex9/classes/classes.json", S3_BUCKET
#     )
#
#     sa.upload_images_from_folder_to_project(
#         project,
#         S3_PREFIX, ["jpg"],
#         annotation_status="QualityCheck",
#         from_s3_bucket=S3_BUCKET
#     )
#     time.sleep(2)
#     assert len(sa.search_images(project)) == 4
