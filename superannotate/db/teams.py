import logging

from ..api import API
from ..exceptions import SABaseException

logger = logging.getLogger("superannotate-python-sdk")

_api = API.get_instance()


def get_default_team():
    """Returns default team

    :return: dict object representing the default team
    :rtype: dict
    """
    response = _api.send_request(req_type='GET', path='/team/DEFAULT')
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't get default team " + response.text
        )
    return response.json()


def search_teams(name_prefix=None):
    """Team name based case-insensitive prefix search for teams.
    If name_prefix is None all the teams will be returned.

    :param name_prefix: name prefix for search
    :type name_prefix: str

    :return: dict objects representing found teams
    :rtype: list
    """
    result_list = []
    params = {'offset': 0}
    if name_prefix is not None:
        params['name'] = name_prefix
    while True:
        response = _api.send_request(
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


def create_team(name, description):
    """Create a new team

    :param name: new team's name
    :type name: str
    :param description: new team's description
    :type description: str

    :return: dict object representing the new team
    :rtype: dict
    """
    data = {"name": name, "description": description, "type": 0}
    response = _api.send_request(req_type='POST', path='/team', json_req=data)
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't create team " + response.text
        )
    return response.json()


def delete_team(team):
    """Deletes team

    :param team: dict object representing team
    :type team: dict
    """
    team_id = team["id"]
    response = _api.send_request(req_type='DELETE', path=f'/team/{team_id}')
    if response.ok:
        logger.info("Successfully deleted team with ID %s.", team_id)
    else:
        raise SABaseException(
            response.status_code, "Couldn't delete team " + response.text
        )
