"""
Main module for consensus computation
"""
import logging
import tempfile
import pandas as pd
from pathlib import Path

from .helpers import image_consensus, consensus_plot
from ..db.exports import prepare_export, download_export
from ..analytics.common import aggregate_annotations_as_df

logger = logging.getLogger("superannotate-python-sdk")


def consensus(
    project_names,
    export_root=None,
    image_list=None,
    annot_type='bbox',
    show_plots=False
):
    """Computes consensus score for each instance of given images that are present in at least 2 of the given projects:    
    
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
    supported_types = ['polygon', 'bbox', 'point']
    if annot_type not in supported_types:
        raise NotImplementedError

    project_dfs = []
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
        project_dfs.append(project_df)

    all_projects_df = pd.concat(project_dfs)
    all_projects_df = all_projects_df[all_projects_df["instanceId"].notna()]

    if image_list is not None:
        all_projects_df = all_projects_df.loc[
            all_projects_df["imageName"].isin(image_list)]

    all_projects_df.query("type == '" + annot_type + "'", inplace=True)

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

    all_projects_df = all_projects_df.groupby(
        ["imageName", "instanceId", "project"]
    )
    all_projects_df = all_projects_df.apply(aggregate_attributes).reset_index(
        drop=True
    )

    unique_images = set(all_projects_df["imageName"])
    all_consensus_data = []
    for image_name in unique_images:
        image_data = image_consensus(all_projects_df, image_name, annot_type)
        all_consensus_data.append(pd.DataFrame(image_data))

    consensus_df = pd.concat(all_consensus_data, ignore_index=True)

    if show_plots:
        consensus_plot(consensus_df, project_names)

    return consensus_df