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

logger = logging.getLogger("superannotate-python-sdk")


def benchmark(
    gt_project_name,
    project_names,
    export_root=None,
    image_list=None,
    annot_type='bbox',
    show_plots=False
):
    """Computes benchmark score for each instance of given images that are present both gt_project_name project and projects in project_names list:    
    
    :param gt_project_name: Project name that contains the ground truth annotations
    :type gt_project_name: str
    :param project_names: list of project names to aggregate through
    :type project_names: list of str
    :param export_root: root export path of the projects
    :type export_root: Pathlike (str or Path)
    :param image_list: List of image names from the projects list that must be used. If None, then all images from the projects list will be used. Default: None
    :type image_list: list
    :param annot_type: Type of annotation instances to consider. Available candidates are: ["bbox", "polygon", "point"]
    :type annot_type: str
    :param show_plots: If True, show plots based on results of consensus computation. Default: False
    :type show_plots: bool

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
            subset=["imageName", "instanceId", "project"], inplace=True
        )
        instance_df["attributes"] = [attributes]
        return instance_df

    supported_types = ['polygon', 'bbox', 'point']
    if annot_type not in supported_types:
        raise NotImplementedError

    if export_root is None:
        with tempfile.TemporaryDirectory() as export_dir:
            gt_project_meta = prepare_export(gt_project_name)
            download_export(gt_project_name, gt_project_meta, export_dir)
            gt_project_df = aggregate_annotations_as_df(export_dir)
    else:
        export_dir = Path(export_root) / gt_project_name
        gt_project_df = aggregate_annotations_as_df(export_dir)
    gt_project_df["project"] = gt_project_name

    benchmark_dfs = []
    for project_name in project_names:
        if export_root is None:
            with tempfile.TemporaryDirectory() as export_dir:
                proj_export_meta = prepare_export(project_name)
                download_export(project_name, proj_export_meta, export_dir)
                project_df = aggregate_annotations_as_df(export_dir)
        else:
            export_dir = Path(export_root) / project_name
            project_df = aggregate_annotations_as_df(export_dir)

        project_df["project"] = project_name
        project_gt_df = pd.concat([project_df, gt_project_df])
        project_gt_df = project_gt_df[project_gt_df["instanceId"].notna()]

        if image_list is not None:
            project_gt_df = project_gt_df.loc[
                project_gt_df["imageName"].isin(image_list)]

        project_gt_df.query("type == '" + annot_type + "'", inplace=True)

        project_gt_df = project_gt_df.groupby(
            ["imageName", "instanceId", "project"]
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
            benchmark_project_df["projectName"] == project_name]

        benchmark_dfs.append(benchmark_project_df)

    benchmark_df = pd.concat(benchmark_dfs, ignore_index=True)

    if show_plots:
        consensus_plot(benchmark_df, project_names)

    return benchmark_df