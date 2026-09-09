"""The scope a token was issued for: what it implies, and how it is read off a key."""

from unittest import TestCase

from superannotate.lib.core.entities.context import API_KEY_AUTH_TYPE
from superannotate.lib.core.entities.context import SDK_AUTH_TYPE
from superannotate.lib.core.entities.context import TokenScope


class TokenScopeTestCase(TestCase):
    def test_only_an_organization_key_carries_no_team(self):
        assert TokenScope.TEAM.carries_team
        assert TokenScope.TEAM_USER.carries_team
        assert TokenScope.LEGACY.carries_team
        assert not TokenScope.ORGANIZATION.carries_team

    def test_only_a_legacy_token_authenticates_as_sdk(self):
        assert TokenScope.LEGACY.auth_type == SDK_AUTH_TYPE
        for scope in (TokenScope.TEAM, TokenScope.TEAM_USER, TokenScope.ORGANIZATION):
            assert scope.auth_type == API_KEY_AUTH_TYPE

    def test_every_scope_has_the_label_telemetry_reports(self):
        assert TokenScope.TEAM.label == "Team API Key"
        assert TokenScope.TEAM_USER.label == "Personal API Key"
        assert TokenScope.ORGANIZATION.label == "Org API Key"
        assert TokenScope.LEGACY.label == "SDK Token"

    def test_formats_as_the_value_it_stands_for(self):
        # Log lines interpolate a scope directly; Enum's own __str__ would print
        # "TokenScope.TEAM" instead of the value the backend uses.
        assert f"{TokenScope.TEAM}" == "team"
        assert TokenScope.TEAM == "team"


class OfApiKeyTestCase(TestCase):
    """Reading the scope off what an API key reports."""

    def test_reads_the_scopes_the_backend_reports(self):
        assert TokenScope.of_api_key("team") is TokenScope.TEAM
        assert TokenScope.of_api_key("teamuser") is TokenScope.TEAM_USER
        assert TokenScope.of_api_key("organization") is TokenScope.ORGANIZATION

    def test_an_unknown_scope_is_not_resolved(self):
        assert TokenScope.of_api_key("something-new") is None
        assert TokenScope.of_api_key(None) is None

    def test_legacy_is_never_read_off_a_key(self):
        # LEGACY is the SDK's own name for a token that resolves offline. An API key
        # reporting it would otherwise authenticate as "sdk" and fail.
        assert TokenScope.of_api_key("legacy") is None
