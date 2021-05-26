"""
Main module for benchmark computation
"""
import logging
import tempfile
import pandas as pd
from pathlib import Path

from .helpers import image_consensus, consensus_plot
from ..db.exports import prepare_export, download_export
from ..analytics.common import aggregate_annotations_as_df
from ..mixp.decorators import Trackable

logger = logging.getLogger("superannotate-python-sdk")


@Trackable
def benchmark(
    project,
    gt_folder,
    folder_names,
    export_root=None,
    image_list=None,
    annot_type='bbox',
    show_plots=False
):
    """Computes benchmark score for each instance of given images that are present both gt_project_name project and projects in folder_names list:    
    
    :param project: project name or metadata of the project
    :type project: str or dict
    :param gt_folder: project folder name that contains the ground truth annotations
    :type gt_folder: str
    :param folder_names: list of folder names in the project for which the scores will be computed
    :type folder_names: list of str
    :param export_root: root export path of the projects
    :type export_root: Pathlike (str or Path)
    :param image_list: List of image names from the projects list that must be used. If None, then all images from the projects list will be used. Default: None
    :type image_list: list
    :param annot_type: Type of annotation instances to consider. Available candidates are: ["bbox", "polygon", "point"]
    :type annot_type: str
    :param show_plots: If True, show plots based on results of consensus computation. Default: False
    :type show_plots: bool

    :return: Pandas DateFrame with columns (creatorEmail, QA, imageName, instanceId, className, area, attribute, folderName, score)
    :rtype: pandas DataFrame
    """
    def aggregate_attributes(instance_df):
        def attribute_to_list(attribute_df):
            attribute_names = list(attribute_df["attributeName"])
            attribute_df["attributeNames"] = len(attribute_df) * [
                attribute_names
            ]
            return attribute_df

        attributes = None
        if not instance_df["attributeGroupName"].isna().all():
            attrib_group_name = instance_df.groupby("attributeGroupName")[[
                "attributeGroupName", "attributeName"
            ]].apply(attribute_to_list)
            attributes = dict(
                zip(
                    attrib_group_name["attributeGroupName"],
                    attrib_group_name["attributeNames"]
                )
            )

        instance_df.drop(
            ["attributeGroupName", "attributeName"], axis=1, inplace=True
        )
        instance_df.drop_duplicates(
            subset=["imageName", "instanceId", "folderName"], inplace=True
        )
        instance_df["attributes"] = [attributes]
        return instance_df

    supported_types = ['polygon', 'bbox', 'point']
    if annot_type not in supported_types:
        raise NotImplementedError

    if export_root is None:
        with tempfile.TemporaryDirectory() as export_dir:
            proj_export_meta = prepare_export(project)
            download_export(project, proj_export_meta, export_dir)
            project_df = aggregate_annotations_as_df(export_dir)
    else:
        project_df = aggregate_annotations_as_df(export_root)

    gt_project_df = project_df[project_df["folderName"] == gt_folder]

    benchmark_dfs = []
    for folder_name in folder_names:
        folder_df = project_df[project_df["folderName"] == folder_name]
        project_gt_df = pd.concat([folder_df, gt_project_df])
        project_gt_df = project_gt_df[project_gt_df["instanceId"].notna()]

        if image_list is not None:
            project_gt_df = project_gt_df.loc[
                project_gt_df["imageName"].isin(image_list)]

        project_gt_df.query("type == '" + annot_type + "'", inplace=True)

        project_gt_df = project_gt_df.groupby(
            ["imageName", "instanceId", "folderName"]
        )
        project_gt_df = project_gt_df.apply(aggregate_attributes).reset_index(
            drop=True
        )
        unique_images = set(project_gt_df["imageName"])
        all_benchmark_data = []
        for image_name in unique_images:
            image_data = image_consensus(project_gt_df, image_name, annot_type)
            all_benchmark_data.append(pd.DataFrame(image_data))

        benchmark_project_df = pd.concat(all_benchmark_data, ignore_index=True)
        benchmark_project_df = benchmark_project_df[
            benchmark_project_df["folderName"] == folder_name]

        benchmark_dfs.append(benchmark_project_df)

    benchmark_df = pd.concat(benchmark_dfs, ignore_index=True)

    if show_plots:
        consensus_plot(benchmark_df, folder_names)

    return benchmark_df