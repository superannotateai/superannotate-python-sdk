import logging

from ..api import API
from ..exceptions import SABaseException
from .project_api import get_project_metadata_bare

logger = logging.getLogger("superannotate-python-sdk")

_api = API.get_instance()


def get_folder_metadata(project, folder_name):
    if not isinstance(project, dict):
        project = get_project_metadata_bare(project)
    team_id, project_id = project["team_id"], project["id"]
    params = {'team_id': team_id, 'project_id': project_id, 'name': folder_name}
    response = _api.send_request(
        req_type='GET', path='/folder/getFolderByName', params=params
    )
    if not response.ok:
        raise SABaseException(
            response.status_code,
            "Couldn't get folder metadata " + response.text
        )
    res = response.json()
    return res


def search_folders(project, folder_name=None, return_metadata=False):
    if not isinstance(project, dict):
        project = get_project_metadata_bare(project)
    team_id, project_id = project["team_id"], project["id"]
    result_list = []
    params = {
        'team_id': team_id,
        'project_id': project_id,
        'offset': 0,
        'name': folder_name,
        'is_root': 0
    }
    total_folders = 0
    while True:
        response = _api.send_request(
            req_type='GET', path='/folders', params=params
        )
        if not response.ok:
            raise SABaseException(
                response.status_code, "Couldn't search folders " + response.text
            )
        response = response.json()
        results_folders = response["data"]
        for r in results_folders:
            if return_metadata:
                result_list.append(r)
            else:
                result_list.append(r["name"])

        total_folders += len(results_folders)
        if response["count"] <= total_folders:
            break

        params["offset"] = total_folders

    return result_list


def create_folder(project, folder_name):
    """Create a new folder in the project.

    :param project: project name or metadata of the project to be deleted
    :type project: str or dict
    :param folder_name: the new folder's name
    :type folder_name: str

    :return: dict object metadata the new folder
    :rtype: dict
    """
    if not isinstance(project, dict):
        project = get_project_metadata_bare(project)
    params = {"team_id": project["team_id"], "project_id": project["id"]}
    data = {"name": folder_name}
    response = _api.send_request(
        req_type='POST', path='/folder', params=params, json_req=data
    )
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't create project " + response.text
        )
    res = response.json()
    if res["name"] != folder_name:
        logger.warning(
            "Created folder has name %s, since folder with name %s already existed.",
            res["name"], folder_name
        )
    return res
