import copy
import logging

from .annotation_classes import search_annotation_classes
from .project_api import (
    get_project_metadata_bare, get_project_metadata_with_users
)
from .projects import get_project_settings, get_project_workflow

logger = logging.getLogger("superannotate-python-sdk")


def get_project_metadata(
    project,
    include_annotation_classes=False,
    include_settings=False,
    include_workflow=False,
    include_contributors=False
):
    """Returns project metadata

    :param project_name: project name
    :type project: str

    :return: metadata of project
    :rtype: dict
    """
    if not isinstance(project, dict):
        project = get_project_metadata_bare(project)
    result = copy.deepcopy(project)
    if include_annotation_classes:
        result["annotation_classes"] = search_annotation_classes(
            project, return_metadata=True
        )
    if include_contributors:
        result["contributors"] = get_project_metadata_with_users(project
                                                                )["users"]
    if include_settings:
        result["settings"] = get_project_settings(project)
    if include_workflow:
        result["workflow"] = get_project_workflow(project)
    return result
