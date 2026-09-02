from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import lib.core as constants
import requests
from lib.core.auth_errors import INVALID_CREDENTIALS_ERROR
from lib.core.auth_errors import INVALID_TEAM_ID_ERROR
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


@dataclass
class TokenContext:
    """The team the client operates in, plus the user acting behind the token."""

    #: None for an organization-scoped client with no team bound (SAORGClient).
    team_id: int | None
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

    @property
    def auth_type_label(self) -> str:
        """Human-readable auth type, for telemetry."""
        if self.is_legacy:
            return "SDK Token"
        if self.is_organization_key:
            return "Org API Key"
        if self.is_team_key:
            return "Team API Key"
        if self.is_personal_key:
            return "Personal API Key"
        return self.auth_type


def resolve_token_context(
    config: ConfigEntity,
    *,
    require_team: bool = True,
    require_organization: bool = False,
) -> TokenContext:
    """Resolve the team (and acting user) a token grants access to.

    Legacy team-owner tokens carry the team id, so they are resolved offline. New-style
    API keys are resolved against the work-management service, which reports the scope
    the key was issued for. The SDK operates within a single team: a team or team-user
    key names that team itself, while an organization key names none, so the team has to
    come from the config (``SAClient(team_id=...)``, ``SA_TEAM_ID``) unless the caller
    opts out with ``require_team=False`` (an org-scoped, team-less client).

    ``require_organization`` rejects any token that does not resolve to an organization
    scope (used by ``SAORGClient``, which only accepts an Organization API key).
    """
    token = config.API_TOKEN
    requested_team_id = config.TEAM_ID
    if is_legacy_token(token):
        return _resolve_legacy_token_context(
            token, requested_team_id, require_organization
        )

    data = _fetch_token_context(config.API_URL, token, config.VERIFY_SSL)
    token_data = data.get("token") or {}
    scope = token_data.get("scope") or {}
    scope_type = token_data.get("scope_type")

    if require_organization and scope_type != ORGANIZATION_SCOPE_TYPE:
        raise AppException(INVALID_CREDENTIALS_ERROR)

    token_team_id = _resolve_scope_team_id(
        scope_type, requested_team_id, scope.get("team_id"), require_team
    )

    logger.debug(f"Token resolved to {scope_type} scope, team {token_team_id}.")
    return TokenContext(
        team_id=int(token_team_id) if token_team_id is not None else None,
        auth_type=API_KEY_AUTH_TYPE,
        user=_build_user(data.get("user"), token_data.get("created_by")),
        scope_type=scope_type,
    )


def _resolve_legacy_token_context(
    token: str, requested_team_id, require_organization: bool
) -> TokenContext:
    """A legacy token resolves offline; it is never organization-scoped."""
    if require_organization:
        raise AppException(INVALID_CREDENTIALS_ERROR)
    team_id = int(token.split("=")[-1])
    _validate_requested_team(requested_team_id, team_id)
    return TokenContext(team_id=team_id, auth_type=SDK_AUTH_TYPE)


def _resolve_scope_team_id(
    scope_type, requested_team_id, token_team_id, require_team: bool
):
    """The team an API key's scope grants access to (None for a team-less org key)."""
    if scope_type == ORGANIZATION_SCOPE_TYPE:
        # An organization key has no team of its own unless the caller names one.
        if requested_team_id is not None:
            return requested_team_id
        if require_team:
            raise AppException(INVALID_CREDENTIALS_ERROR)
        return token_team_id
    if scope_type in TEAM_SCOPED_TYPES:
        # The team_id check keeps a malformed response from resolving to no team at all.
        if token_team_id is None:
            logger.debug(f"Got a {scope_type} scoped token with no team.")
            raise AppException(INVALID_TEAM_ID_ERROR)
        _validate_requested_team(requested_team_id, token_team_id)
        return token_team_id
    # Anything outside the known scopes has no team to operate in.
    logger.debug(f"Rejected a token of {scope_type} scope.")
    raise AppException(INVALID_TEAM_ID_ERROR)


def _validate_requested_team(requested_team_id, token_team_id) -> None:
    """A team_id passed alongside a team-carrying token must agree with it."""
    if requested_team_id is None:
        return
    if int(requested_team_id) != int(token_team_id):
        raise AppException(INVALID_TEAM_ID_ERROR)


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
        if not response.ok:
            logger.debug(
                f"Got {response.status_code} response from backend: {response.text}"
            )
            raise ValueError("non-ok response")
        return response.json()
    except (requests.RequestException, ConnectionError, ValueError):
        raise AppException(INVALID_CREDENTIALS_ERROR) from None


def _build_user(user: dict | None, created_by: str | None) -> UserEntity | None:
    """A team-scoped key has no user behind it, so it falls back to its creator."""
    if user:
        return UserEntity(**user)
    if created_by:
        return UserEntity(id=created_by, email=created_by)
    return None
