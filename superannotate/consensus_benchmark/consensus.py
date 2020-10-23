"""
Main module for consensus computation
"""
import logging
import tempfile
import pandas as pd

from .helpers import image_consensus, consensus_plot
from ..db.exports import prepare_export, get_exports, download_export
from ..analytics.common import aggregate_annotations_as_df
from ..exceptions import SABaseException

logger = logging.getLogger("superannotate-python-sdk")


def consensus(projects, image_list=None, annot_type='bbox', show_plots=False):
    """Computes consensus score for each instance of given images that are present in at least 2 of the given projects:    

    :param input_dir: List of the project names for which the scores will be computed.
    :type input_dir: list
    :param image_list: List of image names from the projects list that must be used. If None, then all images from the projects list will be used. Default: None
    :type output_dir: list
    :param annot_type: Type of annotation instances to consider. Available candidates are: ["bbox", "polygon", "point"]
    :type dataset_format: str
    :param show_plots: If True, show plots based on results of consensus computation. Default: False
    :type output_dir: bool

    """
    supported_types = ['polygon', 'bbox', 'point']
    if annot_type not in supported_types:
        raise NotImplementedError

    project_dfs = []
    for project_name in projects:
        with tempfile.TemporaryDirectory() as export_dir:
            try:
                proj_export_meta = prepare_export(project_name)
            except SABaseException as e:
                logger.info('%s using last export', e.message)
            finally:
                proj_export_meta = get_exports(
                    project_name, return_metadata=True
                )[0]
            download_export(project_name, proj_export_meta, export_dir)
            project_df = aggregate_annotations_as_df(export_dir)
            project_df["project"] = project_name
            project_dfs.append(project_df)

    all_projects_df = pd.concat(project_dfs)
    all_projects_df = all_projects_df[all_projects_df["instanceId"].notna()]

    if image_list is not None:
        all_projects_df = all_projects_df.loc[
            all_projects_df["imageName"].isin(image_list)]

    all_projects_df.query("type == '" + annot_type + "'", inplace=True)

    unique_images = set(all_projects_df["imageName"])
    all_consensus_data = []
    for image_name in unique_images:
        image_data = image_consensus(all_projects_df, image_name, annot_type)
        all_consensus_data.append(pd.DataFrame(image_data))

    consensus_df = pd.concat(all_consensus_data, ignore_index=True)

    if show_plots:
        consensus_plot(consensus_df, projects)

    return consensus_df