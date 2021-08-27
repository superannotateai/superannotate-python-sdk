from ast import literal_eval
from functools import wraps
from inspect import getfullargspec
from pathlib import Path
from typing import get_args
from typing import get_origin
from typing import get_type_hints
from typing import List
from typing import Literal
from typing import Optional
from typing import Tuple
from typing import Union

import boto3
import pandas as pd
from lib.core.exceptions import AppValidationException
from superannotate.lib.app.exceptions import PathError
from superannotate.lib.core import PIXEL_ANNOTATION_POSTFIX
from superannotate.lib.core import VECTOR_ANNOTATION_POSTFIX


def split_project_path(project_path: str) -> Tuple[str, Optional[str]]:
    path = Path(project_path)
    if len(path.parts) > 3:
        raise PathError("There can be no sub folders in the project")
    elif len(path.parts) == 2:
        project_name, folder_name = path.parts
    else:
        project_name, folder_name = path.name, ""

    return project_name, folder_name


def extract_project_folder(user_input: Union[str, dict]) -> Tuple[str, Optional[str]]:
    if isinstance(user_input, str):
        return split_project_path(user_input)
    elif isinstance(user_input, dict):
        project_path = user_input.get("name")
        if not project_path:
            raise PathError("Invalid project path")
        return split_project_path(user_input["name"])
    raise PathError("Invalid project path")


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
            get_local_annotation_paths(path, annotation_paths, recursive)
        for annotation_path in Path(folder_path).glob("*.json"):
            if (
                annotation_path.name.endswith(VECTOR_ANNOTATION_POSTFIX)
                or annotation_path.name.endswith(PIXEL_ANNOTATION_POSTFIX)
            ) and str(annotation_path) not in annotation_paths:
                annotation_paths.append(str(annotation_path))
    return annotation_paths


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
        for annotation in data["Contents"]:
            if annotation["Key"].endswith(VECTOR_ANNOTATION_POSTFIX) or annotation[
                "Key"
            ].endswith(PIXEL_ANNOTATION_POSTFIX):
                annotation_paths.append(annotation["Key"])
    return list(set(annotation_paths))


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


def check_types(obj, **kwargs):
    hints = get_type_hints(obj)

    errors = []
    for attr_name, attr_type in hints.items():
        if attr_name == "return":
            continue
        try:
            if get_origin(attr_type) is list:
                if get_args(attr_type):
                    for elem in kwargs[attr_name]:
                        if type(elem) in get_args(attr_type):
                            continue
                        else:
                            errors.append(f"Invalid input {attr_name}")
                elif not isinstance(kwargs[attr_name], list):
                    errors.append(f"Argument {attr_name} is not of type {attr_type}")
            if get_origin(attr_type) is Literal:
                if kwargs[attr_name] not in get_args(attr_type):
                    errors.append(
                        f'The value of {attr_name} should be {", ".join(get_args(attr_type))}'
                    )
            elif get_origin(attr_type) is Union:
                if kwargs.get(attr_name) and not isinstance(
                    kwargs[attr_name], get_args(attr_type)
                ):
                    errors.append(f"Argument {attr_name} is not of type {attr_type}")
            elif kwargs.get(attr_name) and not isinstance(kwargs[attr_name], attr_type):
                errors.append(f"Argument {attr_name} is not of type {attr_type}")
        except:
            pass
    return errors


def validate_input(decorator):
    @wraps(decorator)
    def wrapped_decorator(*args, **kwargs):
        func_args = getfullargspec(decorator)[0]
        kwargs.update(dict(zip(func_args, args)))
        errors = check_types(decorator, **kwargs)
        if errors:
            raise AppValidationException("\n".join(errors))
        return decorator(**kwargs)

    return wrapped_decorator
