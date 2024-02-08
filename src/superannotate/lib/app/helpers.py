import os
import uuid
from pathlib import Path
from typing import List
from typing import Tuple
from typing import Union

import boto3
import numpy as np
import pandas as pd
from superannotate.lib.app.exceptions import AppException
from superannotate.lib.core import ATTACHED_VIDEO_ANNOTATION_POSTFIX
from superannotate.lib.core import PIXEL_ANNOTATION_POSTFIX
from superannotate.lib.core import VECTOR_ANNOTATION_POSTFIX


def get_annotation_paths(folder_path, s3_bucket=None, recursive=False):
    annotation_paths = []
    if s3_bucket:
        return get_s3_annotation_paths(
            folder_path, s3_bucket, annotation_paths, recursive
        )
    return get_local_annotation_paths(folder_path, set(annotation_paths), recursive)


def get_local_annotation_paths(
    folder_path: Union[str, Path], annotation_paths: set, recursive: bool
) -> List[str]:
    all_items = [*Path(folder_path).glob("*")]
    all_folders = [i for i in all_items if i.is_dir()]
    all_not_folders = [i for i in all_items if not i.is_dir()]
    annotation_paths.update(
        [
            str(i)
            for i in all_not_folders
            if i.name.endswith(
                (
                    VECTOR_ANNOTATION_POSTFIX,
                    PIXEL_ANNOTATION_POSTFIX,
                    ATTACHED_VIDEO_ANNOTATION_POSTFIX,
                )
            )
        ]
    )
    if recursive:
        for folder in all_folders:
            get_local_annotation_paths(
                folder_path=folder,
                annotation_paths=annotation_paths,
                recursive=recursive,
            )
    return list(annotation_paths)


def get_s3_annotation_paths(folder_path, s3_bucket, annotation_paths, recursive):
    s3_client = boto3.client("s3")
    result = s3_client.list_objects(Bucket=s3_bucket, Prefix=folder_path, Delimiter="/")
    result = result.get("CommonPrefixes")
    if recursive and result:
        for folder in result:
            get_s3_annotation_paths(
                folder.get("Prefix"), s3_bucket, annotation_paths, recursive
            )

    paginator = s3_client.get_paginator("list_objects_v2")
    for data in paginator.paginate(Bucket=s3_bucket, Prefix=folder_path):
        for annotation in data.get("Contents", []):
            key = annotation["Key"]
            if (
                key.endswith(VECTOR_ANNOTATION_POSTFIX)
                or key.endswith(PIXEL_ANNOTATION_POSTFIX)
                or key.endswith(ATTACHED_VIDEO_ANNOTATION_POSTFIX)
            ):
                if not recursive and "/" in key[len(folder_path) + 1 :]:
                    continue
                annotation_paths.append(key)
    return list(set(annotation_paths))


def get_name_url_duplicated_from_csv(csv_path):
    image_data = pd.read_csv(csv_path, dtype=str)
    image_data.replace({pd.NA: None}, inplace=True)
    if "url" not in image_data.columns:
        raise AppException("Column 'url' is required")
    image_data = image_data[~image_data["url"].isnull()]
    if "name" in image_data.columns:
        image_data["name"] = (
            image_data["name"]
            .fillna("")
            .apply(lambda cell: cell if str(cell).strip() else str(uuid.uuid4()))
        )
    else:
        image_data["name"] = [str(uuid.uuid4()) for _ in range(len(image_data.index))]

    image_data = pd.DataFrame(image_data, columns=["name", "url", "integration"])
    image_data = image_data.replace(np.nan, None)
    img_names_urls = image_data.to_dict(orient="records")
    duplicate_images = []
    seen = []
    images_to_upload = []
    for i in img_names_urls:
        temp = i["name"]
        i["name"] = i["name"].strip()
        if i["name"] not in seen:
            seen.append(i["name"])
            images_to_upload.append(i)
        else:
            duplicate_images.append(temp)
    return images_to_upload, duplicate_images


def get_tabulation() -> int:
    try:
        return int(os.get_terminal_size().columns / 2)
    except OSError:
        return 48


def wrap_error(errors_list: List[Tuple[str, str]]) -> str:
    tabulation = get_tabulation()
    msgs = []
    for key, value in errors_list:
        _tabulation = tabulation - len(key)
        if not key:
            key, value, _tabulation = value, "", 0
        msgs.append("{}{}{}".format(key, " " * _tabulation, value))
    return "\n".join(msgs)
