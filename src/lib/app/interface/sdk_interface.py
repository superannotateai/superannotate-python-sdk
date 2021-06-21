import logging

import lib.core as constances
from lib.app.serializers import TeamSerializer
from lib.core.response import Response
from lib.infrastructure.controller import Controller
from lib.infrastructure.repositories import ConfigRepository
from lib.infrastructure.services import SuperannotateBackendService


logger = logging.getLogger()


controller = Controller(
    backend_client=SuperannotateBackendService(
        api_url=constances.BACKEND_URL,
        auth_token=ConfigRepository().get_one("token"),
        logger=logger,
    ),
    response=Response(),
)


def get_team_metadata():

    """Returns team metadata

    :return: team metadata
    :rtype: dict
    """
    response = controller.get_team()
    return TeamSerializer(response.data).serialize()


def invite_contributor_to_team(email, admin=False):
    """Invites a contributor to team

    :param email: email of the contributor
    :type email: str
    :param admin: enables admin priviledges for the contributor
    :type admin: bool
    """
    controller.invite_contributor(email, is_admin=admin)


def delete_contributor_to_team_invitation(email):
    """Deletes team contributor invitation

    :param email: invitation email
    :type email: str
    """
    controller.delete_contributor_invitation(email)


def search_team_contributors(email=None, first_name=None, last_name=None, return_metadata=True):
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

    contributors = controller.search_team_contributors(
        email=email, first_name=first_name, last_name=last_name
    )
    if not return_metadata:
        return [contributor["email"] for contributor in contributors]
    return contributors
