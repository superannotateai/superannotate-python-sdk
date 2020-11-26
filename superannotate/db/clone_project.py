import logging

from ..api import API
from ..common import project_type_int_to_str, user_role_int_to_str
from ..exceptions import (
    SABaseException, SAExistingProjectNameException,
    SANonExistingProjectNameException
)
from .annotation_classes import (
    create_annotation_classes_from_classes_json, search_annotation_classes
)
from .project_api import get_project_metadata_bare
from .project_metadata import get_project_metadata
from .projects import (
    get_project_settings, get_project_workflow, set_project_settings,
    set_project_workflow, share_project
)

logger = logging.getLogger("superannotate-python-sdk")
_api = API.get_instance()


def create_project_like_project(
    project_name,
    from_project,
    project_description=None,
    copy_annotation_classes=True,
    copy_settings=True,
    copy_workflow=True,
    copy_project_contributors=False
):
    """Deprecated. Function name changed to clone_project.
    """
    logger.warning("Deprecated. Function name changed to clone_project.")
    clone_project(
        project_name, from_project, project_description,
        copy_annotation_classes, copy_settings, copy_workflow,
        copy_project_contributors
    )


def clone_project(
    project_name,
    from_project,
    project_description=None,
    copy_annotation_classes=True,
    copy_settings=True,
    copy_workflow=True,
    copy_project_contributors=False
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
    :param copy_project_contributors: enables copying project contributors
    :type copy_project_contributors: bool

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
    if not isinstance(from_project, dict):
        from_project = get_project_metadata_bare(from_project)
    if project_description is None:
        project_description = from_project["description"]
    data = {
        "team_id": str(_api.team_id),
        "name": project_name,
        "description": project_description,
        "status": 0,
        "type": from_project["type"]
    }
    response = _api.send_request(
        req_type='POST', path='/project', json_req=data
    )
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't create project " + response.text
        )
    res = response.json()
    logger.info(
        "Created project %s (ID %s) with type %s", res["name"], res["id"],
        project_type_int_to_str(res["type"])
    )
    if copy_settings:
        set_project_settings(res, get_project_settings(from_project))
    if copy_annotation_classes:
        create_annotation_classes_from_classes_json(
            res, search_annotation_classes(from_project, return_metadata=True)
        )
        if copy_workflow:
            set_project_workflow(res, get_project_workflow(from_project))
    if copy_project_contributors:
        from_project = get_project_metadata(from_project, include_users=True)
        for user in from_project["users"]:
            share_project(
                res, user["user_id"], user_role_int_to_str(user["user_role"])
            )

    return res
