import tempfile

import pandas as pd

from .analytics.common import aggregate_annotations_as_df
from .input_converters.conversion import convert_platform


def filter_annotation_instances(
    annotations_dir,
    include_annotation_classes_and_types=None,
    exclude_annotation_classes_and_type=None,
    annotations_platform="Web"
):
    if annotations_platform == "Desktop":
        tmpdir = tempfile.TemporaryDirectory()
        convert_platform(annotations_dir, tmpdir, "Desktop")
        annotations_dir = tmpdir

    df = aggregate_annotations_as_df(annotations_dir)

    if include_annotation_classes_and_types is not None:
        included_dfs = []
        for include_rule in include_annotation_classes_and_types:
            df_new = df.copy()
            if "className" in include_rule:
                df_new = df_new[df_new["class"] == include_rule["className"]]
            if "attributes" in include_rule:
                for attribute in include_rule["attributes"]:
                    df_new = df_new[
                        df_new["attribute_group"] == attribute["groupName"] &
                        df_new["attribute_name"] == attribute["name"]]
            if "type" in include_rule:
                df_new = df_new[df_new["type"] == include_rule["type"]]
            included_dfs.append(df_new)

        df = pd.concat(included_dfs)

    if exclude_annotation_classes_and_type is not None:
        excluded_dfs = []
        for exclude_rule in exclude_annotation_classes_and_type:
            df_new = df.copy()
            if "className" in exclude_rule:
                df_new = df_new[df_new["class"] == exclude_rule["className"]]
            if "attributes" in exclude_rule:
                for attribute in exclude_rule["attributes"]:
                    df_new = df_new[
                        df_new["attribute_group"] == attribute["groupName"] &
                        df_new["attribute_name"] == attribute["name"]]
            if "type" in exclude_rule:
                df_new = df_new[df_new["type"] == exclude_rule["type"]]

        to_exclude = pd.concat(excluded_dfs)
