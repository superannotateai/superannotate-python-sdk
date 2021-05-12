import json
import logging
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .common import aggregate_annotations_as_df
from ..mixp.decorators import Trackable

logger = logging.getLogger("superannotate-python-sdk")


@Trackable
def class_distribution(export_root, project_names, visualize=False):
    """Aggregate distribution of classes across multiple projects.

    :param export_root: root export path of the projects
    :type export_root: Pathlike (str or Path)
    :param project_names: list of project names to aggregate through
    :type project_names: list of str
    :param visualize: enables class histogram plot
    :type visualize: bool
    :return: DataFrame on class distribution with columns ["className", "count"]
    :rtype: pandas DataFrame
    """

    logger.info(
        "Aggregating class distribution accross projects: {}.".format(
            ' '.join(project_names)
        ),
    )

    project_df_list = []
    for project_name in project_names:
        project_root = Path(export_root).joinpath(project_name)
        project_df = aggregate_annotations_as_df(
            project_root, include_classes_wo_annotations=True
        )
        project_df = project_df[["imageName", "instanceId", "className"]]
        project_df["projectName"] = project_name
        project_df_list.append(project_df)

    df = pd.concat(project_df_list, ignore_index=True)

    df["id"] = df["projectName"] + "_" + df["imageName"] + "_" + df[
        "instanceId"].astype(str)
    df = df.groupby("className")['id'].nunique()
    df = df.reset_index().rename(columns={'id': 'count'})
    df = df.sort_values(["count"], ascending=False)

    if visualize:
        fig = px.bar(
            df,
            x='className',
            y='count',
        )
        fig.update_traces(hovertemplate="%{x}: %{y}")
        fig.update_yaxes(title_text="Instance Count")
        fig.update_xaxes(title_text="")
        fig.show()

    return df


@Trackable
def attribute_distribution(export_root, project_names, visualize=False):
    """Aggregate distribution of attributes across multiple projects.

    :param export_root: root export path of the projects
    :type export_root: Pathlike (str or Path)
    :param project_names: list of project names to aggregate through
    :type project_names: list of str
    :param visulaize: enables attribute histogram plot
    :type visualize: bool
    :return: DataFrame on attribute distribution with columns ["className", "attributeGroupName", "attributeName", "count"]
    :rtype: pandas DataFrame
    """

    logger.info(
        "Aggregating attribute distribution accross projects: {}.".format(
            ' '.join(project_names)
        ),
    )

    project_df_list = []
    for project_name in project_names:
        project_root = Path(export_root).joinpath(project_name)
        project_df = aggregate_annotations_as_df(
            project_root, include_classes_wo_annotations=True
        )
        project_df = project_df[[
            "imageName", "instanceId", "className", "attributeGroupName",
            "attributeName"
        ]]
        project_df["projectName"] = project_name
        project_df_list.append(project_df)

    df = pd.concat(project_df_list, ignore_index=True)

    df["id"] = df["projectName"] + "_" + df["imageName"] + "_" + df[
        "instanceId"].astype(str)
    df = df.groupby(["className", "attributeGroupName",
                     "attributeName"])['id'].nunique()
    df = df.reset_index().rename(columns={'id': 'count'})
    df = df.sort_values(["className", "count"], ascending=False)

    if visualize:
        df["attributeId"] = df["className"] + ":" + df["attributeName"]
        fig = px.bar(
            df,
            x="attributeId",
            y="count",
            color="className",
            custom_data=['attributeName']
        )
        fig.update_traces(hovertemplate="%{customdata[0]}: %{y}")
        fig.update_yaxes(title_text="Instance Count")
        fig.update_xaxes(title_text="Attribute", showticklabels=True)
        fig.show()
        del df["attributeId"]

    return df
