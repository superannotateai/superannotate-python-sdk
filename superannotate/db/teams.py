import logging

from ..api import API

from ..exceptions import SABaseException

logger = logging.getLogger("annotateonline-python-sdk")

_api = API.get_instance()


def delete_team(team):
    """Deletes team
    Returns
    -------
    None
    """
    team_id = team["id"]
    response = _api.gen_request(req_type='DELETE', path=f'/team/{team_id}')
    if response.ok:
        logger.info("Successfully deleted team with ID %s.", team_id)
    else:
        raise SABaseException(
            response.status_code, "Couldn't delete team " + response.text
        )


def search_teams(name_prefix=None):
    """Search for teams with prefix name_prefix.
    Returns
    -------
    list:
        list of of Team objects
    """
    result_list = []
    params = {'offset': 0}
    if name_prefix is not None:
        params['name'] = name_prefix
    while True:
        response = _api.gen_request(
            req_type='GET', path='/teams', params=params
        )
        if response.ok:
            res = response.json()
            result_list += res["data"]
            new_len = len(result_list)
            if res["count"] <= new_len:
                break
            params["offset"] = new_len
        else:
            raise SABaseException(
                response.status_code, "Couldn't search teams " + response.text
            )

    return result_list


def create_team(name: str, description: str):
    """Creates a new team
    if annotation_type is vector then a vector project else pixel project
    Returns
    -------
    Team:
        the created team
    """
    data = {"name": name, "description": description, "type": 0}
    response = _api.gen_request(req_type='POST', path='/team', json_req=data)
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't create team " + response.text
        )
    return response.json()


def get_default_team():
    response = _api.gen_request(req_type='GET', path='/team/DEFAULT')
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't get default team " + response.text
        )
    return response.json()
