import os
import platform
import threading
from unittest import TestCase
from unittest.mock import patch

from requests import Response
from requests import Session

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


class TestRequestHeaderIsolation(TestCase):
    """A header a single request needs must not outlive that request.

    x-sa-entity-context names the team, project and folder a request applies to. Written
    onto the shared session it silently rescopes every later call that sets none of its
    own - which is how annotations were uploaded into another project's folder
    (CUST-1182).
    """

    API_URL = "https://api.example.com"

    def setUp(self):
        self.client = HttpClient(
            self.API_URL,
            TokenContext(token="t", team_id=123, scope=TokenScope.LEGACY),
        )
        self.sent = []

        def fake_send(session, request=None, **kwargs):
            self.sent.append(dict(request.headers))
            response = Response()
            response.status_code = 200
            response._content = b"{}"
            return response

        patcher = patch.object(Session, "send", fake_send)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_per_request_header_is_not_left_on_the_session(self):
        self.client.request(
            "items/search", "post", headers={"x-sa-entity-context": "A"}
        )
        self.client.request("folder/getFolderByName", "get", params={"project_id": 9})

        assert self.sent[0]["x-sa-entity-context"] == "A"
        # The second call set none of its own, so it must carry the team-only default.
        assert self.sent[1]["x-sa-entity-context"] == (
            self.client.default_headers["x-sa-entity-context"]
        )
        assert self.client.get_session().headers["x-sa-entity-context"] == (
            self.client.default_headers["x-sa-entity-context"]
        )

    def test_a_per_request_header_does_not_leak_between_projects(self):
        self.client.request(
            "items/search", "post", headers={"x-sa-entity-context": "P1"}
        )
        self.client.request(
            "items/search", "post", headers={"x-sa-entity-context": "P2"}
        )
        self.client.request("folder/getFolderByName", "get")

        assert [h["x-sa-entity-context"] for h in self.sent[:2]] == ["P1", "P2"]
        assert self.sent[2]["x-sa-entity-context"] not in ("P1", "P2")

    def test_a_file_upload_suppresses_the_json_content_type_for_that_call_only(self):
        self.client.request("items/upload", "post", files={"f": b"x"})
        self.client.request("items/search", "post")

        assert "Content-Type" not in self.sent[0]
        assert self.sent[1]["Content-Type"] == "application/json"


class TestSessionIsolation(TestCase):
    """requests.Session is not thread-safe, so no two threads may share one.

    Sessions used to be cached against threading.get_ident(), which CPython recycles as
    soon as a thread exits - and run_async() starts and joins a thread per async
    operation, so unrelated threads were handed each other's session.
    """

    API_URL = "https://api.example.com"

    def setUp(self):
        self.client = HttpClient(
            self.API_URL,
            TokenContext(token="t", team_id=123, scope=TokenScope.LEGACY),
        )

    def test_one_thread_reuses_its_own_session(self):
        assert self.client.get_session() is self.client.get_session()

    def test_no_session_is_shared_between_threads(self):
        # References are held so a dead thread's session cannot be freed and a new one
        # allocated at the same address, which would make identity comparison lie.
        sessions, idents = [], []

        def work():
            idents.append(threading.get_ident())
            sessions.append(self.client.get_session())

        for _ in range(25):
            thread = threading.Thread(target=work)
            thread.start()
            thread.join()

        assert len(set(map(id, sessions))) == len(sessions)
        # The point of the test: the idents these threads ran under were reused.
        assert len(set(idents)) < len(idents)

    def test_concurrent_threads_get_distinct_sessions(self):
        sessions = []
        barrier = threading.Barrier(4)

        def work():
            barrier.wait()
            sessions.append(self.client.get_session())

        threads = [threading.Thread(target=work) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert len(set(map(id, sessions))) == 4
