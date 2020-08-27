# sudo apt install awscli
# aws configure
# aws s3 cp ~/work/val2017/ s3://hovnatan-test/ff --recursive

from pathlib import Path

from urllib.parse import urlparse

import boto3

import superannotate as sa

sa.init(Path.home() / ".superannotate" / "config.json")

PROJECT_NAME = "test_ya90"
s3_client = boto3.client('s3')

S3_PREFIX = 'frex9'
S3_BUCKET = 'hovnatan-test'


def test_from_s3_upload():
    paginator = s3_client.get_paginator('list_objects_v2')

    projects = sa.search_projects(PROJECT_NAME)
    for project in projects:
        sa.delete_project(project)

    project = sa.create_project(PROJECT_NAME, "hk", 1)
    sa.create_annotation_classes_from_classes_json(
        project, "frex9/classes/classes.json", S3_BUCKET
    )

    f = urlparse("s3://hovnatan-test/frex9")
    sa.upload_images_from_folder_to_project(
        project,
        f.path[1:], ["jpg"],
        annotation_status=3,
        from_s3_bucket=f.netloc
    )
    files = []
    response_iterator = paginator.paginate(Bucket=S3_BUCKET, Prefix=S3_PREFIX)
    for response in response_iterator:
        if 'Contents' in response:
            for object_data in response['Contents']:
                key = object_data['Key']
                files.append(key)

    assert len(files) == 4
    assert len(sa.search_images(project)) == 1
