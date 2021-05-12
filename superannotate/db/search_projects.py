import logging

from ..api import API
from ..exceptions import SABaseException

logger = logging.getLogger("superannotate-python-sdk")

_api = API.get_instance()
from ..mixp.decorators import Trackable


@Trackable
def search_projects(
    name=None, return_metadata=False, include_complete_image_count=False
):
    """Project name based case-insensitive search for projects.
    If **name** is None, all the projects will be returned.

    :param name: search string
    :type name: str
    :param return_metadata: return metadata of projects instead of names
    :type return_metadata: bool

    :return: project names or metadatas
    :rtype: list of strs or dicts
    """
    result_list = []
    limit = 1000
    params = {
        'team_id': str(_api.team_id),
        'offset': 0,
        'limit': limit,
        'completeImagesCount': include_complete_image_count
    }
    if name is not None:
        params['name'] = name
    while True:
        response = _api.send_request(
            req_type='GET', path='/projects', params=params
        )
        if response.ok:
            new_results = response.json()
            result_list += new_results["data"]
            params["offset"] += limit
            if params["offset"] >= new_results["count"]:
                break
        else:
            raise SABaseException(
                response.status_code,
                "Couldn't search projects." + response.text
            )
    if return_metadata:
        return result_list
    else:
        return [x["name"] for x in result_list]
