from pathlib import Path

import pandas as pd
import plotly.express as px
from lib.app.mixp.decorators import Trackable
from superannotate.lib.app.exceptions import AppException
from superannotate.lib.core import DEPRICATED_DOCUMENT_VIDEO_MESSAGE
from superannotate.logger import get_default_logger

from .common import aggregate_image_annotations_as_df

logger = get_default_logger()


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

    json_paths = list(Path(str(export_root)).glob("*.json"))
    if (
        json_paths
        and "___pixel.json" not in json_paths[0].name
        and "___objects.json" not in json_paths[0].name
    ):
        raise AppException(DEPRICATED_DOCUMENT_VIDEO_MESSAGE)

    logger.info(
        "Aggregating class distribution accross projects: {}.".format(
            " ".join(project_names)
        ),
    )

    project_df_list = []
    for project_name in project_names:
        project_root = Path(export_root).joinpath(project_name)
        project_df = aggregate_image_annotations_as_df(
            project_root, include_classes_wo_annotations=True
        )
        project_df = project_df[["imageName", "instanceId", "className"]]
        project_df["projectName"] = project_name
        project_df_list.append(project_df)

    df = pd.concat(project_df_list, ignore_index=True)

    df["id"] = (
        df["projectName"] + "_" + df["imageName"] + "_" + df["instanceId"].astype(str)
    )
    df = df.groupby("className")["id"].nunique()
    df = df.reset_index().rename(columns={"id": "count"})
    df = df.sort_values(["count"], ascending=False)

    if visualize:
        fig = px.bar(df, x="className", y="count",)
        fig.update_traces(hovertemplate="%{x}: %{y}")
        fig.update_yaxes(title_text="Instance Count")
        fig.update_xaxes(title_text="")
        fig.show()

    return df
