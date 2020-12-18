import logging

from ..api import API
from ..exceptions import (
    SAExistingProjectNameException, SANonExistingProjectNameException
)
from .project_api import get_project_metadata_bare
from .project_metadata import get_project_metadata
from .projects import create_project_from_metadata

logger = logging.getLogger("superannotate-python-sdk")
_api = API.get_instance()


def clone_project(
    project_name,
    from_project,
    project_description=None,
    copy_annotation_classes=True,
    copy_settings=True,
    copy_workflow=True,
    copy_contributors=False
):
    """Create a new project in the team using annotation classes and settings from from_project.

    :param project_name: new project's name
    :type project_name: str
    :param from_project: the name or metadata of the project being used for duplication
    :type from_project: str or dict
    :param project_description: the new project's description. If None, from_project's
                                description will be used
    :type project_description: str
    :param copy_annotation_classes: enables copying annotation classes
    :type copy_annotation_classes: bool
    :param copy_settings: enables copying project settings
    :type copy_settings: bool
    :param copy_workflow: enables copying project workflow
    :type copy_workflow: bool
    :param copy_contributors: enables copying project contributors
    :type copy_contributors: bool

    :return: dict object metadata of the new project
    :rtype: dict
    """
    try:
        get_project_metadata_bare(project_name)
    except SANonExistingProjectNameException:
        pass
    else:
        raise SAExistingProjectNameException(
            0, "Project with name " + project_name +
            " already exists. Please use unique names for projects to use with SDK."
        )
    metadata = get_project_metadata(
        from_project, copy_annotation_classes, copy_settings, copy_workflow,
        copy_contributors
    )
    metadata["name"] = project_name
    if project_description is not None:
        metadata["description"] = project_description

    return create_project_from_metadata(metadata)
