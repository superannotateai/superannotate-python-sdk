from pathlib import Path
from typing import Optional
from typing import Tuple

import boto3
from lib.app.exceptions import PathError
from lib.core import PIXEL_ANNOTATION_POSTFIX
from lib.core import VECTOR_ANNOTATION_POSTFIX


def split_project_path(project_path: str) -> Tuple[str, Optional[str]]:
    path = Path(project_path)
    if len(path.parts) > 3:
        raise PathError("There can be no subfolders in the project")
    elif len(path.parts) == 2:
        project_name, folder_name = path.parts
    else:
        project_name, folder_name = path.name, ""

    return project_name, folder_name


def get_annotation_paths(folder_path, s3_bucket=None, recursive=False):
    annotation_paths = []
    if s3_bucket:
        return get_s3_annotation_paths(
            folder_path, s3_bucket, annotation_paths, recursive
        )
    return get_local_annotation_paths(folder_path, annotation_paths, recursive)


def get_local_annotation_paths(folder_path, annotation_paths, recursive):
    for path in Path(folder_path).glob("*"):
        if recursive and path.is_dir():
            return get_local_annotation_paths(path, annotation_paths, recursive)
        for annotation_path in Path(folder_path).glob("*.json"):
            if annotation_path.name.endswith(
                VECTOR_ANNOTATION_POSTFIX
            ) or annotation_path.name.endswith(PIXEL_ANNOTATION_POSTFIX):
                annotation_paths.append(annotation_path)
        return annotation_paths


def get_s3_annotation_paths(folder_path, s3_bucket, annotation_paths, recursive):
    s3_client = boto3.client("s3")
    result = s3_client.list_objects(Bucket=s3_bucket, Prefix=folder_path, Delimiter="/")
    result = result.get("CommonPrefixes")
    if recursive and result:
        for folder in result:
            return get_s3_annotation_paths(
                folder.get("Prefix"), s3_bucket, annotation_paths, recursive
            )

    paginator = s3_client.get_paginator("list_objects_v2")
    for data in paginator.paginate(Bucket=s3_bucket, Prefix=folder_path):
        for annotation in data["Contents"]:
            if annotation["key"].endswith(VECTOR_ANNOTATION_POSTFIX) or annotation[
                "key"
            ].endswith(PIXEL_ANNOTATION_POSTFIX):
                annotation_paths.append(annotation["key"])
