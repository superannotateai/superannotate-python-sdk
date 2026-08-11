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

#: Token scopes that carry a team: "team" is a Team key, "teamuser" a Personal key.
TEAM_SCOPED_TYPES = ("team", "teamuser")

ORGANIZATION_API_KEY_ERROR = (
    "SAClient does not accept an Organization API key — it requires a Team or "
    "Personal API key."
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
) -> TokenContext:
    """Resolve the team (and acting user) a token grants access to.

    Legacy team-owner tokens carry the team id, so they are resolved offline. New-style
    API keys are resolved against the work-management service, which reports the scope
    the key was issued for. The SDK operates within a single team, so a key that is not
    scoped to one is rejected.
    """
    if is_legacy_token(token):
        return TokenContext(team_id=int(token.split("=")[-1]), auth_type=SDK_AUTH_TYPE)

    data = _fetch_token_context(api_url, token, verify_ssl)
    token_data = data.get("token") or {}
    scope = token_data.get("scope") or {}
    scope_type = token_data.get("scope_type")
    token_team_id = scope.get("team_id")

    # Anything outside the allowlist (an organization key, today) has no team to operate
    # in; the team_id check keeps a malformed response from resolving to no team at all.
    if scope_type not in TEAM_SCOPED_TYPES or token_team_id is None:
        logger.debug(f"Rejected a token of {scope_type} scope.")
        raise AppException(ORGANIZATION_API_KEY_ERROR)

    logger.debug(f"Token resolved to {scope_type} scope, team {token_team_id}.")
    return TokenContext(
        team_id=int(token_team_id),
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
