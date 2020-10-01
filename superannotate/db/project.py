import logging

from ..api import API
from ..exceptions import (
    SABaseException, SAExistingProjectNameException,
    SANonExistingProjectNameException
)

logger = logging.getLogger("superannotate-python-sdk")
_api = API.get_instance()


def _get_project_metadata(project):
    team_id, project_id = project["team_id"], project["id"]
    params = {'team_id': str(team_id)}
    response = _api.send_request(
        req_type='GET', path=f'/project/{project_id}', params=params
    )
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't get project." + response.text
        )
    res = response.json()
    return res


def search_projects(name=None, return_metadata=False):
    """Project name based case-insensitive search for projects.
    If **name** is None, all the projects will be returned.

    :param name: search string
    :type name: str
    :param return_metadata: return metadata of images instead of names
    :type return_metadata: bool

    :return: project names or metadatas
    :rtype: list of strs or dicts
    """
    result_list = []
    params = {'team_id': str(_api.team_id), 'offset': 0}
    if name is not None:
        params['name'] = name
    while True:
        response = _api.send_request(
            req_type='GET', path='/projects', params=params
        )
        if response.ok:
            new_results = response.json()
            result_list += new_results["data"]
            if response.json()["count"] <= len(result_list):
                break
            params["offset"] = len(result_list)
        else:
            raise SABaseException(
                response.status_code,
                "Couldn't search projects." + response.text
            )
    if return_metadata:
        return result_list
    else:
        return [x["name"] for x in result_list]


def get_project_metadata(project_name):
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
        return _get_project_metadata(results[0])
    else:
        raise SANonExistingProjectNameException(
            0, "Project with name " + project_name + " doesn't exist."
        )
