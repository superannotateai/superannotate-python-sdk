from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import lib.core as constants
import requests
from lib.core.entities.base import is_legacy_token
from lib.core.entities.project import UserEntity
from lib.core.exceptions import AppException

if TYPE_CHECKING:
    from lib.core.entities.base import ConfigEntity

logger = logging.getLogger("sa")

SDK_AUTH_TYPE = "sdk"
API_KEY_AUTH_TYPE = "api_key"

URL_TOKEN_CONTEXT = "users/me"

#: A key issued for the team itself, with no user behind it. It acts on the team's
#: behalf, so the backend denies operations that only a user can perform (changing a
#: team admin's permissions, for one).
TEAM_SCOPE_TYPE = "team"
#: A key issued for one user of a team; it acts as that user.
TEAM_USER_SCOPE_TYPE = "teamuser"
#: A key issued for an organization. It carries no team, so the team to operate in has
#: to be given explicitly.
ORGANIZATION_SCOPE_TYPE = "organization"
#: Token scopes that carry a team, and therefore need no explicit team_id.
TEAM_SCOPED_TYPES = (TEAM_SCOPE_TYPE, TEAM_USER_SCOPE_TYPE)

ORGANIZATION_MISSING_TEAM_CONTEXT_ERROR = (
    'Team context not provided. An Organization API key requires a "team_id".'
)
UNRESOLVED_TEAM_ERROR = (
    "Unable to resolve the team the provided token grants access to."
)
TEAM_ID_MISMATCH_ERROR = (
    'The provided "team_id" ({team_id}) does not match the team the token grants '
    "access to ({token_team_id})."
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
    #: Scope the key was issued for ("team", "teamuser", "organization"); None for a
    #: legacy token, whose scope is not reported by the backend.
    scope_type: str | None = None

    @property
    def is_legacy(self) -> bool:
        return self.auth_type == SDK_AUTH_TYPE

    @property
    def is_team_key(self) -> bool:
        """Whether the token acts as the team rather than as a user."""
        return self.scope_type == TEAM_SCOPE_TYPE

    @property
    def is_personal_key(self) -> bool:
        """Whether the token acts as one specific user of the team."""
        return self.scope_type == TEAM_USER_SCOPE_TYPE

    @property
    def is_organization_key(self) -> bool:
        """Whether the token was issued for an organization rather than a team."""
        return self.scope_type == ORGANIZATION_SCOPE_TYPE


def resolve_token_context(config: ConfigEntity) -> TokenContext:
    """Resolve the team (and acting user) a token grants access to.

    Legacy team-owner tokens carry the team id, so they are resolved offline. New-style
    API keys are resolved against the work-management service, which reports the scope
    the key was issued for. The SDK operates within a single team: a team or team-user
    key names that team itself, while an organization key names none, so the team has to
    come from the config (``SAClient(team_id=...)``, ``SA_TEAM_ID``).
    """
    token = config.API_TOKEN
    requested_team_id = config.TEAM_ID
    if is_legacy_token(token):
        team_id = int(token.split("=")[-1])
        _validate_requested_team(requested_team_id, team_id)
        return TokenContext(team_id=team_id, auth_type=SDK_AUTH_TYPE)

    data = _fetch_token_context(config.API_URL, token, config.VERIFY_SSL)
    token_data = data.get("token") or {}
    scope = token_data.get("scope") or {}
    scope_type = token_data.get("scope_type")
    token_team_id = scope.get("team_id")

    if scope_type == ORGANIZATION_SCOPE_TYPE:
        # An organization key has no team of its own; the caller picks the one to use.
        if requested_team_id is None:
            raise AppException(ORGANIZATION_MISSING_TEAM_CONTEXT_ERROR)
        token_team_id = requested_team_id
    elif scope_type in TEAM_SCOPED_TYPES:
        # The team_id check keeps a malformed response from resolving to no team at all.
        if token_team_id is None:
            logger.debug(f"Got a {scope_type} scoped token with no team.")
            raise AppException(UNRESOLVED_TEAM_ERROR)
        _validate_requested_team(requested_team_id, token_team_id)
    else:
        # Anything outside the known scopes has no team to operate in.
        logger.debug(f"Rejected a token of {scope_type} scope.")
        raise AppException(UNRESOLVED_TEAM_ERROR)

    logger.debug(f"Token resolved to {scope_type} scope, team {token_team_id}.")
    return TokenContext(
        team_id=int(token_team_id),
        auth_type=API_KEY_AUTH_TYPE,
        user=_build_user(data.get("user"), token_data.get("created_by")),
        scope_type=scope_type,
    )


def _validate_requested_team(requested_team_id, token_team_id) -> None:
    """A team_id passed alongside a team-carrying token must agree with it."""
    if requested_team_id is None:
        return
    if int(requested_team_id) != int(token_team_id):
        raise AppException(
            TEAM_ID_MISMATCH_ERROR.format(
                team_id=requested_team_id, token_team_id=token_team_id
            )
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
