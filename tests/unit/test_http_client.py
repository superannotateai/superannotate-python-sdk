import os
import platform
from unittest import TestCase
from unittest.mock import patch

from src.superannotate.lib.infrastructure.services.http_client import HttpClient


class TestHttpClient(TestCase):
    def setUp(self):
        self.api_url = "https://api.example.com"
        self.team_id = 123
        self.token = f"test_token={self.team_id}"

    @patch.dict(os.environ, {"sa_version": "1.0.0", "SA_ENV": "test"})
    def test_default_headers_with_env(self):
        client = HttpClient(self.api_url, self.token, self.team_id)
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
            self.api_url, "sa_public_id_secret", self.team_id, auth_type="api_key"
        )
        headers = client.default_headers

        assert headers["Authorization"] == "sa_public_id_secret"
        assert headers["authtype"] == "api_key"
        assert f"Team: {self.team_id}" in headers["User-Agent"]

    @patch.dict(os.environ, {"sa_version": "2.0.0"}, clear=True)
    def test_default_headers_without_env(self):
        client = HttpClient(self.api_url, self.token, self.team_id)
        headers = client.default_headers

        expected_user_agent = (
            f"Python-SDK-Version: 2.0.0; Python: {platform.python_version()};"
            f"OS: {platform.system()}; Team: {self.team_id}"
        )

        assert headers["User-Agent"] == expected_user_agent
        assert "Env:" not in headers["User-Agent"]

    def test_default_headers_no_version(self):
        with patch.dict(os.environ, {}, clear=True):
            client = HttpClient(self.api_url, self.token, self.team_id)
            headers = client.default_headers

            expected_user_agent = (
                f"Python-SDK-Version: None; Python: {platform.python_version()};"
                f"OS: {platform.system()}; Team: {self.team_id}"
            )
            assert headers["User-Agent"] == expected_user_agent
