from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from lib.core.entities.project import UserEntity

#: Wire values of the ``authtype`` header, which is how a token authenticates rather
#: than what it was issued for. Derived from the scope; see TokenScope.auth_type.
SDK_AUTH_TYPE = "sdk"
API_KEY_AUTH_TYPE = "api_key"


class TokenScope(str, Enum):
    """What a token was issued for.

    This is the one fact that decides how a token authenticates, whether it carries
    its own team, and what it is allowed to do - so it is held once, as a scope,
    rather than spread across an auth type and a nullable scope string.
    """

    #: Issued for the team itself, with no user behind it. It acts on the team's
    #: behalf, so the backend denies operations only a user can perform (changing a
    #: team admin's permissions, for one).
    TEAM = "team"
    #: Issued for one user of a team; it acts as that user.
    TEAM_USER = "teamuser"
    #: Issued for an organization. It carries no team, so the team to operate in has
    #: to be named explicitly.
    ORGANIZATION = "organization"
    #: A legacy team-owner token, which carries its team id in the token itself and
    #: resolves offline. The backend reports no scope for one, so this is the SDK's
    #: own name for it rather than a value it receives.
    LEGACY = "legacy"

    def __str__(self) -> str:
        # Formats as the value it stands for, so log lines and test skip messages read
        # "team" rather than "TokenScope.TEAM".
        return self.value

    @classmethod
    def of_api_key(cls, scope_type: str | None) -> TokenScope | None:
        """The scope an API key reports, or None if it is not one the SDK knows.

        LEGACY is never a valid answer: a legacy token is recognised from its own
        shape, never from a scope the backend reports.
        """
        try:
            scope = cls(scope_type)
        except ValueError:
            return None
        return None if scope is cls.LEGACY else scope

    @property
    def carries_team(self) -> bool:
        """Whether the scope names its own team, so no explicit team_id is needed."""
        return self is not TokenScope.ORGANIZATION

    @property
    def auth_type(self) -> str:
        """The ``authtype`` a token of this scope authenticates with."""
        return SDK_AUTH_TYPE if self is TokenScope.LEGACY else API_KEY_AUTH_TYPE

    @property
    def label(self) -> str:
        """Human-readable name, for telemetry."""
        return _SCOPE_LABELS[self]


_SCOPE_LABELS = {
    TokenScope.TEAM: "Team API Key",
    TokenScope.TEAM_USER: "Personal API Key",
    TokenScope.ORGANIZATION: "Org API Key",
    TokenScope.LEGACY: "SDK Token",
}


@dataclass(frozen=True)
class TokenContext:
    """Everything a client needs to act on the caller's behalf: the resolved form of
    the credentials in ``ConfigEntity``.

    Clients are built from one of these rather than from loose token / team_id /
    auth_type arguments, so "which team am I in, and as whom" is answered in a single
    place. A team-less, organization-scoped client is expressed as ``team_id=None``
    here instead of being re-derived at every call site.

    Frozen on purpose: a client caches its HTTP session with the headers of the context
    it was built from, so re-scoping a live context would leave session and context
    disagreeing. Resolve a new context (and a new client) for a different team.
    """

    #: The API key or legacy token sent as the Authorization header.
    token: str
    #: The team every request is scoped to. None for an organization-scoped client with
    #: no team bound (SAORGClient), which scopes its requests to no team at all.
    team_id: int | None
    #: What the token was issued for; compare against TokenScope directly.
    scope: TokenScope
    #: The user acting behind the token; None until it has been resolved.
    user: UserEntity | None = None

    @property
    def auth_type(self) -> str:
        """The ``authtype`` header this context authenticates with."""
        return self.scope.auth_type
