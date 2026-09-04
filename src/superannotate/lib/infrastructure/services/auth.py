from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import lib.core as constants
import requests
from lib.core import INVALID_CREDENTIALS_ERROR
from lib.core import INVALID_TEAM_ID_ERROR
from lib.core.entities.base import is_legacy_token
from lib.core.entities.context import API_KEY_AUTH_TYPE
from lib.core.entities.context import TokenContext
from lib.core.entities.context import TokenScope
from lib.core.entities.project import UserEntity
from lib.core.exceptions import SAAuthError

if TYPE_CHECKING:
    from lib.core.entities.base import ConfigEntity

logger = logging.getLogger("sa")

URL_TOKEN_CONTEXT = "users/me"


def resolve_team_context(config: ConfigEntity) -> TokenContext:
    """The team a token grants access to, plus the user acting behind it.

    A legacy team-owner token carries its team id, so it resolves offline. An API key
    resolves against the work-management service, which reports the scope it was issued
    for: a team or team-user key names its own team, while an organization key names
    none, so the team has to come from the config (``SAClient(team_id=...)``,
    ``SA_TEAM_ID``).
    """
    token = config.API_TOKEN
    if is_legacy_token(token):
        team_id = int(token.split("=")[-1])
        _validate_requested_team(config.TEAM_ID, team_id)
        return TokenContext(token=token, team_id=team_id, scope=TokenScope.LEGACY)

    scope, scope_team_id, user = _resolve_api_key(config)
    if scope is None:
        raise SAAuthError(INVALID_TEAM_ID_ERROR)
    team_id = _team_for_scope(scope, config.TEAM_ID, scope_team_id)
    logger.debug(f"Token resolved to {scope} scope, team {team_id}.")
    return TokenContext(token=token, team_id=int(team_id), scope=scope, user=user)


def resolve_organization_context(config: ConfigEntity) -> TokenContext:
    """An organization-scoped session, bound to no team, for ``SAORGClient``.

    Only an Organization API key is accepted: every other token acts within one team
    and so cannot act for the organization. Any ``team_id`` in the config is ignored -
    an organization client operates outside any single team by definition.
    """
    if is_legacy_token(config.API_TOKEN):
        raise SAAuthError(INVALID_CREDENTIALS_ERROR)
    scope, _, user = _resolve_api_key(config)
    if scope is not TokenScope.ORGANIZATION:
        raise SAAuthError(INVALID_CREDENTIALS_ERROR)
    logger.debug("Token resolved to organization scope, with no team.")
    return TokenContext(token=config.API_TOKEN, team_id=None, scope=scope, user=user)


def _resolve_api_key(
    config: ConfigEntity,
) -> tuple[TokenScope | None, int | None, UserEntity | None]:
    """What an API key reports: the scope it was issued for (None when the SDK does not
    know it), the team that scope names, and the user behind the key.
    """
    data = _fetch_token_context(config.API_URL, config.API_TOKEN, config.VERIFY_SSL)
    token_data = data.get("token") or {}
    reported_scope = token_data.get("scope_type")
    scope = TokenScope.of_api_key(reported_scope)
    if scope is None:
        logger.debug(f"Got a token of unknown {reported_scope} scope.")
    return (
        scope,
        (token_data.get("scope") or {}).get("team_id"),
        _build_user(data.get("user"), token_data.get("created_by")),
    )


def _team_for_scope(scope: TokenScope, requested_team_id, scope_team_id) -> int:
    """The team a team-scoped client operates in."""
    if not scope.carries_team:
        # An organization key has no team of its own, so the caller has to name one.
        if requested_team_id is None:
            raise SAAuthError(INVALID_CREDENTIALS_ERROR)
        return requested_team_id
    # The team_id check keeps a malformed response from resolving to no team at all.
    if scope_team_id is None:
        logger.debug(f"Got a {scope} scoped token with no team.")
        raise SAAuthError(INVALID_TEAM_ID_ERROR)
    _validate_requested_team(requested_team_id, scope_team_id)
    return scope_team_id


def _validate_requested_team(requested_team_id, token_team_id) -> None:
    """A team_id passed alongside a team-carrying token must agree with it."""
    if requested_team_id is None:
        return
    if int(requested_team_id) != int(token_team_id):
        raise SAAuthError(INVALID_TEAM_ID_ERROR)


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
                f"Got {response.status_code} response from backend {url}: {response.text}"
            )
            raise ValueError("non-ok response")
        return response.json()
    except (requests.RequestException, ConnectionError, ValueError):
        raise SAAuthError(INVALID_CREDENTIALS_ERROR) from None


def _build_user(user: dict | None, created_by: str | None) -> UserEntity | None:
    """A team-scoped key has no user behind it, so it falls back to its creator."""
    if user:
        return UserEntity(**user)
    if created_by:
        return UserEntity(id=created_by, email=created_by)
    return None
