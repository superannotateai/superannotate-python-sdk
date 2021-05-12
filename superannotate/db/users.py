import logging

from ..api import API
from ..exceptions import SABaseException

logger = logging.getLogger("superannotate-python-sdk")
from ..mixp.decorators import Trackable

_api = API.get_instance()


@Trackable
def search_team_contributors(
    email=None, first_name=None, last_name=None, return_metadata=False
):
    """Search for contributors in the team

    :param email: filter by email
    :type email: str
    :param first_name: filter by first name
    :type first_name: str
    :param last_name: filter by last name
    :type last_name: str

    :return: metadata of found users
    :rtype: list of dicts
    """
    result_list = []
    params = {'team_id': _api.team_id, 'offset': 0}
    if email is not None:
        params['email'] = email
    if first_name is not None:
        params['first_name'] = first_name
    if last_name is not None:
        params['last_name'] = last_name

    while True:
        response = _api.send_request(
            req_type='GET', path='/users', params=params
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
                response.status_code,
                "Couldn't search projects. " + response.text
            )

    if return_metadata:
        return result_list
    else:
        return [x["email"] for x in result_list]


def get_team_contributor_metadata(email):
    users = search_team_contributors(email, return_metadata=True)
    results = []
    for user in users:
        if user["email"] == email:
            results.append(user)

    if len(results) == 0:
        raise SABaseException(0, "No user with email " + email + " found.")
    if len(results) > 1:
        raise SABaseException(0, "Email " + email + " malformed.")
    return results[0]
