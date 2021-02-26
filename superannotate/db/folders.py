from ..api import API
from ..exceptions import SABaseException
from .project_api import get_project_metadata_bare

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
    params = {'team_id': team_id, 'project_id': project_id, 'offset': 0}
    total_got = 0
    total_folders = 0
    while True:
        response = _api.send_request(
            req_type='GET', path='/images', params=params
        )
        if not response.ok:
            raise SABaseException(
                response.status_code, "Couldn't search images " + response.text
            )
        response = response.json()
        images = response["images"]
        folders = response["folders"]

        results_folders = folders["data"]
        for r in results_folders:
            if folder_name is not None and r["name"] != folder_name:
                continue
            if return_metadata:
                result_list.append(r)
            else:
                result_list.append(r["name"])

        total_folders += len(results_folders)
        if folders["count"] <= total_folders:
            break

        total_got += len(images["data"]) + len(results_folders)
        params["offset"] = total_got

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
    return res
