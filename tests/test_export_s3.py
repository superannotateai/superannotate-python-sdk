from pathlib import Path

import boto3

import superannotate as sa

sa.init(Path.home() / ".annotateonline" / "config.json")
s3_client = boto3.client('s3')

S3_PREFIX = 'frex9'
S3_BUCKET = 'hovnatan-test'


def test_export_s3(tmpdir):
    paginator = s3_client.get_paginator('list_objects_v2')
    response_iterator = paginator.paginate(Bucket=S3_BUCKET, Prefix=S3_PREFIX)
    for response in response_iterator:
        if 'Contents' in response:
            for object_data in response['Contents']:
                key = object_data['Key']
                s3_client.delete_object(Bucket=S3_BUCKET, Key=key)
    tmpdir = Path(tmpdir)
    team = sa.get_default_team()
    project = sa.search_projects(team, "Example Project 1")[0]
    images = sa.search_images(project)
    for img in images:
        sa.set_image_annotation_status(img, 3)

    new_export = sa.get_exports(project)[-1]
    # new_export = sa.prepare_export(project)
    sa.download_export(new_export, S3_PREFIX, to_s3_bucket=S3_BUCKET)

    files = []
    response_iterator = paginator.paginate(Bucket=S3_BUCKET, Prefix=S3_PREFIX)
    for response in response_iterator:
        if 'Contents' in response:
            for object_data in response['Contents']:
                key = object_data['Key']
                files.append(key)
    output_path = tmpdir / S3_PREFIX
    output_path.mkdir()
    sa.download_export(new_export, output_path)
    local_files = list(output_path.rglob("*.*"))

    assert len(local_files) == len(files)
