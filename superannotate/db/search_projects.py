import logging

from ..api import API
from ..exceptions import (SABaseException)

logger = logging.getLogger("superannotate-python-sdk")
_api = API.get_instance()


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
