import logging

from ..api import API
from ..common import user_role_int_to_str
from ..exceptions import SABaseException

logger = logging.getLogger("superannotate-python-sdk")

_api = API.get_instance()

from ..mixp.decorators import Trackable


@Trackable
def invite_contributor_to_team(email, admin=False):
    """Invites a contributor to team

    :param email: email of the contributor
    :type email: str
    :param admin: enables admin priviledges for the contributor
    :type admin: bool
    """
    user_role = 2 if admin else 3
    data = {'email': email, 'user_role': user_role}
    response = _api.send_request(
        req_type='POST', path=f'/team/{_api.team_id}/invite', json_req=data
    )
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't invite to team. " + response.text
        )

    return response.json()


@Trackable
def get_team_metadata():
    """Returns team metadata

    :param convert_users_role_to_string: convert integer team users' roles to human comprehensible strings
    :type convert_users_role_to_string: bool
    :return: team metadata
    :rtype: dict
    """
    response = _api.send_request(req_type='GET', path=f'/team/{_api.team_id}')
    if not response.ok:
        raise SABaseException(
            response.status_code, "Couldn't get team metadata. " + response.text
        )

    res = response.json()
    res["user_role"] = user_role_int_to_str(res["user_role"])
    for user in res["users"]:
        user["user_role"] = user_role_int_to_str(user["user_role"])
    for user in res["pending_invitations"]:
        user["user_role"] = user_role_int_to_str(user["user_role"])

    return res


@Trackable
def delete_contributor_to_team_invitation(email):
    """Deletes team contributor invitation

    :param email: invitation email
    :type email: str
    """
    team_metadata = get_team_metadata()
    for invite in team_metadata["pending_invitations"]:
        if invite["email"] == email:
            break
    else:
        raise SABaseException(0, "Couldn't find user " + email + " invitation")

    data = {'token': invite["token"], 'e_mail': invite['email']}  # pylint: disable=undefined-loop-variable
    response = _api.send_request(
        req_type='DELETE', path=f'/team/{_api.team_id}/invite', json_req=data
    )
    if not response.ok:
        raise SABaseException(
            response.status_code,
            "Couldn't delete contributor invite. " + response.text
        )
