from pathlib import Path
import os

import pytest
import boto3

import superannotate as sa

sa.init(Path.home() / ".superannotate" / "config.json")

TEST_PROJECT_NAME = "test_direct_s3_upload"
S3_BUCKET = 'superannotate-python-sdk-test'
S3_FOLDER = 'sample_project_vector'
S3_FOLDER_STRESS = 'ff'


def test_direct_s3_upload():
    projects_found = sa.search_projects(TEST_PROJECT_NAME, return_metadata=True)
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(TEST_PROJECT_NAME, "a", "Vector")
    print(project["id"])

    csv = (Path.home() / ".aws" / "credentials").read_text().splitlines()

    access_key_id = csv[1].split(" = ")[1]
    access_secret = csv[2].split(" = ")[1]

    sa.upload_images_from_s3_bucket_to_project(
        project, access_key_id, access_secret, S3_BUCKET, S3_FOLDER
    )
    s3_client = boto3.client('s3')
    paginator = s3_client.get_paginator('list_objects_v2')
    response_iterator = paginator.paginate(Bucket=S3_BUCKET, Prefix=S3_FOLDER)
    on_s3 = []
    for response in response_iterator:
        if 'Contents' in response:
            for object_data in response['Contents']:
                key = object_data['Key']
                if key[-4:] in [".jpg", ".png"]:
                    on_s3.append(key)

    assert len(on_s3) == sa.get_project_image_count(project)


@pytest.mark.skipif(
    "AO_TEST_LEVEL" not in os.environ or
    os.environ["AO_TEST_LEVEL"] != "stress",
    reason="Requires env variable to be set"
)
def test_direct_s3_upload_stress():
    projects_found = sa.search_projects(
        TEST_PROJECT_NAME + " stress", return_metadata=True
    )
    for pr in projects_found:
        sa.delete_project(pr)

    project = sa.create_project(TEST_PROJECT_NAME + " stress", "a", "Vector")

    csv = (Path.home() /
           "hovnatan_aws.csv").read_text().splitlines()[1].split(",")

    sa.upload_images_from_s3_bucket_to_project(
        project, csv[2], csv[3], S3_BUCKET, S3_FOLDER_STRESS
    )
    s3_client = boto3.client('s3')
    paginator = s3_client.get_paginator('list_objects_v2')
    response_iterator = paginator.paginate(
        Bucket=S3_BUCKET, Prefix=S3_FOLDER_STRESS
    )
    on_s3 = []
    for response in response_iterator:
        if 'Contents' in response:
            for object_data in response['Contents']:
                key = object_data['Key']
                if key[-4:] == ".jpg":
                    on_s3.append(key)

    assert len(on_s3) == sa.get_project_image_count(project)
