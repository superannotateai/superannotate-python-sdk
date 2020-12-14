import logging

from .. import common
from ..api import API
from ..exceptions import (
    SABaseException, SAExistingProjectNameException,
    SANonExistingProjectNameException
)
from .search_projects import search_projects

logger = logging.getLogger("superannotate-python-sdk")
_api = API.get_instance()


def get_project_metadata_bare(project_name):
    """Returns project metadata

    :param project_name: project name
    :type project: str

    :return: metadata of project
    :rtype: dict
    """
    projects = search_projects(project_name, return_metadata=True)
    results = []
    for project in projects:
        if project["name"] == project_name:
            results.append(project)

    if len(results) > 1:
        raise SAExistingProjectNameException(
            0, "Project name " + project_name +
            " is not unique. To use SDK please make project names unique."
        )
    elif len(results) == 1:
        res = results[0]
        res["type"] = common.project_type_int_to_str(res["type"])
        res["user_role"] = common.user_role_int_to_str(res["user_role"])
        return res
    else:
        raise SANonExistingProjectNameException(
            0, "Project with name " + project_name + " doesn't exist."
        )


def get_project_metadata_with_users(project_metadata):
    team_id, project_id = project_metadata["team_id"], project_metadata["id"]
    params = {'team_id': str(team_id)}
    response = _api.send_request(
        req_type='GET', path=f'/project/{project_id}', params=params
    )
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't get project." + response.text
        )
    res = response.json()
    for contributor in res["users"]:
        contributor["user_role"] = common.user_role_int_to_str(
            contributor["user_role"]
        )
    return res
