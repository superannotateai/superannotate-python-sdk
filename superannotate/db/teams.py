import logging

from ..api import API
from ..exceptions import SABaseException

logger = logging.getLogger("superannotate-python-sdk")

_api = API.get_instance()


def invite_contributor_to_team(email, admin=False):
    """Invites a contributor to team

    :param email: email of the contributor
    :type project: str
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


# def delete_team_contributor_invitation(invitation):
#     """Deletes team contributor invitation

#     :param invite: invitation metadata returned from invite_contributor_to_team
#     :type project: dict
#     """
#     data = {'token': invitation["token"], 'e_mail': invitation['email']}
#     response = _api.send_request(
#         req_type='DELETE', path=f'/team/{_api.team_id}/invite', json_req=data
#     )
#     if not response.ok:
#         raise SABaseException(
#             response.status_code,
#             "Couldn't delete contributor invite. " + response.text
#         )
