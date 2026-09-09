import os
import platform
from unittest import TestCase
from unittest.mock import patch

from src.superannotate.lib.core.entities.context import TokenContext
from src.superannotate.lib.core.entities.context import TokenScope
from src.superannotate.lib.infrastructure.services.http_client import HttpClient


class TestHttpClient(TestCase):
    def setUp(self):
        self.api_url = "https://api.example.com"
        self.team_id = 123
        self.token = f"test_token={self.team_id}"
        self.context = TokenContext(
            token=self.token, team_id=self.team_id, scope=TokenScope.LEGACY
        )

    @patch.dict(os.environ, {"sa_version": "1.0.0", "SA_ENV": "test"})
    def test_default_headers_with_env(self):
        client = HttpClient(self.api_url, self.context)
        headers = client.default_headers

        expected_user_agent = (
            f"Python-SDK-Version: 1.0.0; Python: {platform.python_version()};"
            f"OS: {platform.system()}; Team: {self.team_id}; Env: test"
        )

        assert headers["Authorization"] == self.token
        assert headers["authtype"] == "sdk"
        assert headers["Content-Type"] == "application/json"
        assert headers["User-Agent"] == expected_user_agent

    @patch.dict(os.environ, {"sa_version": "1.0.0"})
    def test_default_headers_auth_type(self):
        client = HttpClient(
            self.api_url,
            TokenContext(
                token="sa_public_id_secret",
                team_id=self.team_id,
                scope=TokenScope.TEAM,
            ),
        )
        headers = client.default_headers

        assert headers["Authorization"] == "sa_public_id_secret"
        assert headers["authtype"] == "api_key"
        assert f"Team: {self.team_id}" in headers["User-Agent"]

    @patch.dict(os.environ, {"sa_version": "2.0.0"}, clear=True)
    def test_default_headers_without_env(self):
        client = HttpClient(self.api_url, self.context)
        headers = client.default_headers

        expected_user_agent = (
            f"Python-SDK-Version: 2.0.0; Python: {platform.python_version()};"
            f"OS: {platform.system()}; Team: {self.team_id}"
        )

        assert headers["User-Agent"] == expected_user_agent
        assert "Env:" not in headers["User-Agent"]

    def test_default_headers_no_version(self):
        with patch.dict(os.environ, {}, clear=True):
            client = HttpClient(self.api_url, self.context)
            headers = client.default_headers

            expected_user_agent = (
                f"Python-SDK-Version: None; Python: {platform.python_version()};"
                f"OS: {platform.system()}; Team: {self.team_id}"
            )
            assert headers["User-Agent"] == expected_user_agent


class TestTeamScoping(TestCase):
    """The context is the only place a team is named: a client with one scopes every
    request to it, a team-less (organization) client scopes to nothing."""

    API_URL = "https://api.example.com"

    def _client(self, team_id, scope=TokenScope.TEAM):
        return HttpClient(
            self.API_URL,
            TokenContext(
                token="sa_public_id_secret",
                team_id=team_id,
                scope=scope,
            ),
        )

    def test_a_team_context_is_sent_as_a_header_and_a_query_param(self):
        client = self._client(123)

        assert client.team_id == 123
        assert client.default_query_params == {"team_id": 123}
        # base64 of {"team_id": 123}
        assert client.default_headers["x-sa-entity-context"] == (
            "eyJ0ZWFtX2lkIjogMTIzfQ=="
        )
        assert "Team: 123" in client.default_headers["User-Agent"]

    def test_a_team_less_context_scopes_requests_to_no_team(self):
        client = self._client(None, scope=TokenScope.ORGANIZATION)

        assert client.team_id is None
        assert client.default_query_params == {}
        assert "x-sa-entity-context" not in client.default_headers
        assert "Team:" not in client.default_headers["User-Agent"]

    def test_default_query_params_cannot_be_mutated_through_a_request(self):
        # request() copies them per call, so one request cannot leak params into the next.
        client = self._client(123)
        params = client.default_query_params
        params["project_id"] = 7

        assert client.default_query_params == {"team_id": 123}
