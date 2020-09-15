from pathlib import Path

import boto3

import superannotate as sa

sa.init(Path.home() / ".superannotate" / "config.json")
s3_client = boto3.client('s3')

S3_PREFIX = 'frex9'
S3_BUCKET = 'hovnatan-test'
PROJECT_NAME = "Example project test"


def test_export_s3(tmpdir):
    paginator = s3_client.get_paginator('list_objects_v2')
    response_iterator = paginator.paginate(Bucket=S3_BUCKET, Prefix=S3_PREFIX)
    for response in response_iterator:
        if 'Contents' in response:
            for object_data in response['Contents']:
                key = object_data['Key']
                s3_client.delete_object(Bucket=S3_BUCKET, Key=key)
    tmpdir = Path(tmpdir)
    project = sa.create_project(PROJECT_NAME, "test", "Vector")

    sa.upload_images_from_folder_to_project(
        project,
        Path("./tests/sample_project_vector"),
        annotation_status="InProgress"
    )
    sa.create_annotation_classes_from_classes_json(
        project, Path("./tests/sample_project_vector/classes/classes.json")
    )
    sa.upload_annotations_from_folder_to_project(
        project, Path("./tests/sample_project_vector")
    )
    images = sa.search_images(project)
    for img in images:
        sa.set_image_annotation_status(project, img, 'QualityCheck')

    new_export = sa.prepare_export(project, include_fuse=True)
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


def test_from_s3_upload():
    projects = sa.search_projects(PROJECT_NAME)
    for project in projects:
        sa.delete_project(project)

    project = sa.create_project(PROJECT_NAME, "hk", "Vector")
    sa.create_annotation_classes_from_classes_json(
        project, "frex9/classes/classes.json", S3_BUCKET
    )

    sa.upload_images_from_folder_to_project(
        project,
        S3_PREFIX, ["jpg"],
        annotation_status="QualityCheck",
        from_s3_bucket=S3_BUCKET
    )
    assert len(sa.search_images(project)) == 4
