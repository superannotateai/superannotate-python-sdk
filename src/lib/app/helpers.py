from ast import literal_eval
from pathlib import Path
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

import boto3
import pandas as pd
from lib.app.exceptions import PathError
from lib.core import PIXEL_ANNOTATION_POSTFIX
from lib.core import VECTOR_ANNOTATION_POSTFIX


def split_project_path(project_path: str) -> Tuple[str, Optional[str]]:
    path = Path(project_path)
    if len(path.parts) > 3:
        raise PathError("There can be no sub folders in the project")
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


def get_local_annotation_paths(
    folder_path: Union[str, Path], annotation_paths: List, recursive: bool
) -> List[str]:
    for path in Path(folder_path).glob("*"):
        if recursive and path.is_dir():
            return get_local_annotation_paths(path, annotation_paths, recursive)
        for annotation_path in Path(folder_path).glob("*.json"):
            if annotation_path.name.endswith(
                VECTOR_ANNOTATION_POSTFIX
            ) or annotation_path.name.endswith(PIXEL_ANNOTATION_POSTFIX):
                annotation_paths.append(str(annotation_path))
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


def reformat_metrics_json(data, name):
    continuous_metrics = []
    per_evaluation_metrics = []
    for item in data:
        for key in item:
            try:
                item[key] = literal_eval(item[key])
            except Exception as e:
                pass
        if "data_time" in item and item["eta_seconds"] != 0:
            continuous_metrics += [item]
        else:
            per_evaluation_metrics += [item]
    continuous_metrics_df = pd.DataFrame.from_dict(continuous_metrics)
    per_evaluation_metrics_df = pd.DataFrame.from_dict(per_evaluation_metrics)
    continuous_metrics_df = drop_non_plotable_cols(continuous_metrics_df)
    per_evaluation_metrics_df = drop_non_plotable_cols(per_evaluation_metrics_df)
    continuous_metrics_df["model"] = name
    per_evaluation_metrics_df["model"] = name
    if "total_loss" in per_evaluation_metrics_df:
        per_evaluation_metrics_df = per_evaluation_metrics_df.drop(columns="total_loss")

    per_evaluation_metrics_df = per_evaluation_metrics_df.dropna(axis="rows")
    return continuous_metrics_df, per_evaluation_metrics_df


def drop_non_plotable_cols(df):
    for column in df:
        if metric_is_plottable(column):
            continue
        df = df.drop(columns=column)
    return df


def metric_is_plottable(key):
    if key == "total_loss" or "mIoU" in key or "mAP" in key or key == "iteration":
        return True
    return False
