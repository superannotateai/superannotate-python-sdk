from __future__ import annotations

import logging
from dataclasses import dataclass

import lib.core as constants
import requests
from lib.core.entities.base import is_legacy_token
from lib.core.entities.project import UserEntity
from lib.core.exceptions import AppException

logger = logging.getLogger("sa")

SDK_AUTH_TYPE = "sdk"
API_KEY_AUTH_TYPE = "api_key"

URL_TOKEN_CONTEXT = "users/me"

#: Token scopes that carry a team, and therefore need no explicit team_id.
TEAM_SCOPED_TYPES = ("team", "teamuser")

TEAM_CONTEXT_REQUIRED_ERROR = (
    "The provided token is not scoped to a team, and the SDK operates within a team. "
    "Provide a team by passing team_id to SAClient(...), by setting the SA_TEAM_ID "
    "environment variable, or by adding SA_TEAM_ID to the config file."
)
TEAM_ID_MISMATCH_ERROR = (
    "The provided team_id ({provided}) does not match the team the token is scoped "
    "to ({actual}). Omit team_id to use the token's own team."
)
AUTHENTICATION_ERROR = (
    "Unable to authenticate the provided token. Please verify your credentials."
)


@dataclass
class TokenContext:
    """The team the client operates in, plus the user acting behind the token."""

    team_id: int
    auth_type: str
    user: UserEntity | None = None

    @property
    def is_legacy(self) -> bool:
        return self.auth_type == SDK_AUTH_TYPE


def resolve_token_context(
    api_url: str,
    token: str,
    verify_ssl: bool = True,
    team_id: int | None = None,
) -> TokenContext:
    """Resolve the team (and acting user) a token grants access to.

    Legacy team-owner tokens carry the team id, so they are resolved offline. New-style
    API keys are resolved against the work-management service, which reports the scope
    the key was issued for.
    """
    if is_legacy_token(token):
        token_team_id = int(token.split("=")[-1])
        if team_id is not None and team_id != token_team_id:
            raise AppException(
                TEAM_ID_MISMATCH_ERROR.format(provided=team_id, actual=token_team_id)
            )
        return TokenContext(team_id=token_team_id, auth_type=SDK_AUTH_TYPE)

    data = _fetch_token_context(api_url, token, verify_ssl)
    token_data = data.get("token") or {}
    scope = token_data.get("scope") or {}
    scope_type = token_data.get("scope_type")
    token_team_id = scope.get("team_id")

    if token_team_id is None:
        # Organization-scoped (or any other team-less) key: the caller has to say which
        # team to work in.
        if team_id is None:
            raise AppException(TEAM_CONTEXT_REQUIRED_ERROR)
        resolved_team_id = team_id
    else:
        if team_id is not None and int(team_id) != int(token_team_id):
            raise AppException(
                TEAM_ID_MISMATCH_ERROR.format(provided=team_id, actual=token_team_id)
            )
        resolved_team_id = int(token_team_id)

    logger.debug(f"Token resolved to {scope_type} scope, team {resolved_team_id}.")
    return TokenContext(
        team_id=resolved_team_id,
        auth_type=API_KEY_AUTH_TYPE,
        user=_build_user(data.get("user"), token_data.get("created_by")),
    )


def _get_work_management_url(api_url: str) -> str:
    # The token scope has to be resolved before there is a client to ask, so the
    # work-management host is derived here as well as in the service provider.
    if api_url != constants.BACKEND_URL:
        return "https://work-management-api.devsuperannotate.com/api/v1/"
    return "https://work-management-api.superannotate.com/api/v1/"


def _fetch_token_context(api_url: str, token: str, verify_ssl: bool) -> dict:
    url = f"{_get_work_management_url(api_url)}{URL_TOKEN_CONTEXT}"
    try:
        response = requests.post(
            url,
            json={},
            headers={
                "Authorization": token,
                "authtype": API_KEY_AUTH_TYPE,
                "Content-Type": "application/json",
            },
            verify=verify_ssl,
        )
    except (requests.RequestException, ConnectionError) as e:
        raise AppException(f"Unable to authenticate the provided token: {e}.")
    if not response.ok:
        logger.debug(
            f"Got {response.status_code} response from backend: {response.text}"
        )
        raise AppException(AUTHENTICATION_ERROR)
    try:
        return response.json()
    except ValueError:
        raise AppException(AUTHENTICATION_ERROR)


def _build_user(user: dict | None, created_by: str | None) -> UserEntity | None:
    """A team-scoped key has no user behind it, so it falls back to its creator."""
    if user:
        return UserEntity(**user)
    if created_by:
        return UserEntity(id=created_by, email=created_by)
    return None
