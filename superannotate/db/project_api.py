import logging

from .. import common
from ..api import API
from ..exceptions import (
    SABaseException, SAExistingProjectNameException, SAIncorrectProjectArgument,
    SANonExistingProjectNameException
)
from .search_projects import search_projects

logger = logging.getLogger("superannotate-python-sdk")
_api = API.get_instance()


def get_project_metadata_bare(project_name, include_complete_image_count=False):
    """Returns project metadata

    :param project_name: project name
    :type project: str

    :return: metadata of project
    :rtype: dict
    """
    projects = search_projects(
        project_name,
        return_metadata=True,
        include_complete_image_count=include_complete_image_count
    )
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


def get_folder_metadata(project, folder_name):
    """Returns folder metadata

    :param project: project name
    :type project: str
    :param folder_name: folder's name
    :type folder_name: str

    :return: metadata of folder
    :rtype: dict
    """
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


def get_project_and_folder_metadata(project):
    """Returns project and folder metadata tuple. If folder part is empty, 
    than returned folder part is set to None.

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param folder_name: folder's name
    :type folder_name: str

    :return: metadata of folder
    :rtype: dict
    """
    if isinstance(project, dict):
        folder = None
    elif isinstance(project, tuple):
        if len(project) != 2:
            raise SAIncorrectProjectArgument(project)
        project, folder = project
        if not isinstance(project, dict):
            raise SAIncorrectProjectArgument(project)
        if folder is not None and not isinstance(project, dict):
            raise SAIncorrectProjectArgument(project)
    elif isinstance(project, str):
        parts = project.split('/')
        if len(parts) == 1:
            project_name = parts[0]
            project = get_project_metadata_bare(project_name)
            folder = None
        elif len(parts) == 2:
            project_name, folder_name = parts
            project = get_project_metadata_bare(project_name)
            folder = get_folder_metadata(project, folder_name)
        else:
            raise SAIncorrectProjectArgument(project)
    else:
        raise SAIncorrectProjectArgument(project)
    return project, folder


def search_folders(project, folder_name=None, return_metadata=False):
    """Folder name based case-insensitive search for folders in project.

    :param project: project name
    :type project: str
    :param folder_name: the new folder's name
    :type folder_name: str. If  None, all the folders in the project will be returned.
    :param return_metadata: return metadata of folders instead of names
    :type return_metadata: bool

    :return: folder names or metadatas
    :rtype: list of strs or dicts
    """
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

    :param project: project name
    :type project: str
    :param folder_name: the new folder's name
    :type folder_name: str

    :return: dict object metadata the new folder
    :rtype: dict
    """
    if not isinstance(project, dict):
        project = get_project_metadata_bare(project)
    params = {"team_id": project["team_id"], "project_id": project["id"]}
    name_changed = False
    if len(
        set(folder_name).intersection(
            common.SPECIAL_CHARACTERS_IN_PROJECT_FOLDER_NAMES
        )
    ) > 0:
        logger.warning(
            "New folder name has special characters. Special characters will be replaced by underscores."
        )
        name_changed = True

    data = {"name": folder_name}
    response = _api.send_request(
        req_type='POST', path='/folder', params=params, json_req=data
    )
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't create project " + response.text
        )
    res = response.json()

    if res["name"] != folder_name and not name_changed:
        logger.warning(
            "Created folder has name %s, since folder with name %s already existed.",
            res["name"], folder_name
        )
    logger.info("Folder %s created in project %s", res["name"], project["name"])
    return res


def delete_folders(project, folder_names):
    """Delete folder in project.

    :param project: project name
    :type project: str
    :param folder_names: to be deleted folders' names
    :type folder_names: list of strs
    """
    if not isinstance(project, dict):
        project = get_project_metadata_bare(project)
    all_folders_metadata = search_folders(project, return_metadata=True)
    if not isinstance(folder_names, list):
        raise SABaseException(0, "folder_names should be a list of strings")

    folder_ids_to_delete = [
        f["id"] for f in all_folders_metadata if f["name"] in folder_names
    ]

    params = {"team_id": project["team_id"], "project_id": project["id"]}
    data = {"folder_ids": folder_ids_to_delete}
    response = _api.send_request(
        req_type='PUT',
        path='/image/delete/images',
        params=params,
        json_req=data
    )
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't delete folders " + response.text
        )
    logger.info(
        "Folders %s deleted in project %s", folder_names, project["name"]
    )


def rename_folder(project, new_folder_name):
    """Renames folder in project.

    :param project: project name or folder path (e.g., "project1/folder1")
    :type project: str
    :param new_folder_name: folder's new name
    :type new_folder_name: str
    """
    project, project_folder = get_project_and_folder_metadata(project)
    params = {"team_id": project["team_id"], "project_id": project["id"]}
    data = {"name": new_folder_name}
    response = _api.send_request(
        req_type='PUT',
        path=f'/folder/{project_folder["id"]}',
        params=params,
        json_req=data
    )
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't rename folder " + response.text
        )
    logger.info(
        "Folder %s renamed to %s in project %s", project_folder["name"],
        new_folder_name, project["name"]
    )
