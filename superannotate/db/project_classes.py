import logging
import json
import io
from pathlib import Path

import boto3

from ..api import API
from ..exceptions import AOBaseException

logger = logging.getLogger("annotateonline-python-sdk")

_api = API.get_instance()


def create_class(project, name, color, attribute_groups=None):
    """ Create class in project from a ProjectClass instance
    """
    team_id, project_id = project["team_id"], project["id"]
    logger.info(
        "Creating class in project ID %s with name %s", project_id, name
    )
    params = {
        'team_id': team_id,
        'project_id': project_id,
    }
    data = {
        "classes":
            [
                {
                    "name":
                        name,
                    "color":
                        color,
                    "attribute_groups":
                        attribute_groups if attribute_groups is not None else []
                }
            ]
    }
    response = _api.gen_request(
        req_type='POST', path='/classes', params=params, json_req=data
    )
    if not response.ok:
        raise AOBaseException(
            response.status_code, "Couldn't create class " + response.text
        )
    res = response.json()
    new_class = res[0]
    return new_class


def create_classes_from_classes_json(
    project, path_to_classes_json, from_s3_bucket=None
):
    """ Create classes in project from a annotateonline classes.json
    """
    project_id = project["id"]
    logger.info(
        "Creating classes in project ID %s from %s.", project_id,
        path_to_classes_json
    )
    old_class_id_to_new_conversion = {}
    if from_s3_bucket is None:
        classes = json.load(open(path_to_classes_json))
    else:
        from_session = boto3.Session()
        from_s3 = from_session.resource('s3')
        file = io.BytesIO()
        from_s3_object = from_s3.Object(from_s3_bucket, path_to_classes_json)
        from_s3_object.download_fileobj(file)
        file.seek(0)
        classes = json.load(file)

    for cl in classes:
        new_class = create_class(
            project, cl["name"], cl["color"], cl["attribute_groups"]
        )
        old_id = cl["id"]
        new_id = new_class["id"]
        old_class_id_to_new_conversion[old_id] = new_id
    return old_class_id_to_new_conversion


def search_classes(project, name_prefix=None):
    """Search for name_prefix prefixed classes in the project.
    Returns
    -------
    list of Project.ProjectClass
    """
    result_list = []
    team_id, project_id = project["team_id"], project["id"]
    params = {'team_id': team_id, 'project_id': project_id, 'offset': 0}
    if name_prefix is not None:
        params['name'] = name_prefix
    while True:
        response = _api.gen_request(
            req_type='GET', path='/classes', params=params
        )
        if not response.ok:
            raise AOBaseException(
                response.status_code, "Couldn't search classes " + response.text
            )
        res = response.json()
        result_list += res["data"]
        new_len = len(result_list)
        # for r in result_list:
        #     print(r)
        if res["count"] <= new_len:
            break
        params["offset"] = new_len
    return result_list


def download_classes_json(project, folder):
    """Download classes.json to path
    Returns
    -------
    None
    """
    project_id = project["id"]
    logger.info(
        "Downloading classes.json from project ID %s to folder %s.", project_id,
        folder
    )
    clss = search_classes(project)
    json.dump(clss, open(Path(folder) / "classes.json", "w"), indent=2)
