"""SAClient.explore - the Explore query language namespace.

Nothing here touches the network: the HTTP client, the controller or Tracker._track
are replaced, so what is under test is the SDK's own behaviour - paging, subset
resolution, argument checks, the response model, deprecations and telemetry names.
"""

import os
import warnings
from unittest import TestCase
from unittest.mock import MagicMock
from unittest.mock import patch

from lib.app.interface.base_interface import Tracker
from lib.app.interface.sdk.explore import Explore
from lib.core.entities import FolderEntity
from lib.core.entities import ProjectEntity
from lib.core.entities import SubSetEntity
from lib.core.service_types import ExploreItem
from lib.core.service_types import ExploreQueryResponse
from lib.core.service_types import ServiceResponse
from lib.core.usecases import ExploreQueryCountUseCase
from lib.core.usecases import ExploreQueryUseCase
from lib.infrastructure.services.explore import ExploreService
from superannotate import AppException
from superannotate import SAClient

ITEM = {
    "id": 196560932,
    "name": "TEST_00001",
    "folder_id": 867191,
    "comments": [],
    "annotation_status": 2,
    "annotator_id": None,
    "annotator_name": None,
    "path": "custom_llm",
    "qa_id": None,
    "approval_status": 0,
    "createdAt": "2026-08-04T03:50:53.000Z",
    "updatedAt": "2026-09-02T10:37:18.000Z",
    "meta": {"integration_id": None},
    "instances": [],
    "componentGenerationStatuses": {},
    "custom_metadata": {},
    "subset_ids": [],
    "category_id": [],
    "category_name": None,
    "assignment": [],
    "last_action": {
        "date": "2026-09-02T10:37:17.217Z",
        "email": "test@superannotate.com",
    },
    "score": [],
    "is_pinned": 0,
    "folder_name": "root",
    "is_root_folder": 1,
    "lores": "custom_llm",
    "thumbnail": "custom_llm",
}

EXPECTED_KEYS = {
    "id",
    "name",
    "folder_id",
    "comments",
    "annotation_status",
    "path",
    "approval_status",
    "createdAt",
    "updatedAt",
    "meta",
    "instances",
    "custom_metadata",
    "subset_ids",
    "category_id",
    "category_name",
    "assignment",
    "last_action",
    "score",
    "is_pinned",
    "folder_name",
    "is_root_folder",
}

PROJECT = ProjectEntity(id=1476298, name="Project", type=8)
ROOT = FolderEntity(id=1, name="root", is_root=True)
FOLDER = FolderEntity(id=1767159, name="folder", is_root=False)


def _page(n: int, status=200):
    return ExploreQueryResponse(status=status, res_data=[ITEM] * n)


class ExploreItemTestCase(TestCase):
    def test_keeps_only_the_documented_keys_as_sent(self):
        dumped = ExploreItem(**ITEM).model_dump()

        assert set(dumped) == EXPECTED_KEYS
        assert dumped["annotation_status"] == 2
        assert dumped["is_pinned"] == 0
        assert dumped["meta"] == {"integration_id": None}
        assert dumped["last_action"] == ITEM["last_action"]


class ExploreServiceTestCase(TestCase):
    def setUp(self):
        self.client = MagicMock()
        self.client.api_url = "https://api.devsuperannotate.com"
        self.service = ExploreService(self.client)

    def test_query_pages_by_25_until_a_short_page(self):
        pages = iter([_page(25), _page(25), _page(3)])
        sent = []

        def request(url, method, params, data, content_type):
            sent.append(dict(data))  # the service reuses one body dict across pages
            return next(pages)

        self.client.request.side_effect = request

        response = self.service.explore_query(
            PROJECT, FOLDER, query='_status = "InProgress"', subset_id=7
        )

        assert response.ok
        assert len(response.data) == 53
        calls = self.client.request.call_args_list
        assert [body["image_index"] for body in sent] == [0, 25, 50]
        url, method = calls[0].args
        assert url == "https://explore-service.devsuperannotate.com/api/v3/items/search"
        assert method == "post"
        assert calls[0].kwargs["params"] == {
            "project_id": 1476298,
            "includeFolderNames": True,
            "folder_id": 1767159,
            "subset_id": 7,
        }
        assert sent[0]["limit"] == 25
        assert sent[0]["query"] == '_status = "InProgress"'

    def test_query_returns_the_backend_error(self):
        self.client.request.return_value = ExploreQueryResponse(
            status=400,
            res_error="Data may be incomplete. Resync from the Explore page to ensure accuracy.",
        )

        response = self.service.explore_query(PROJECT, query="x")

        assert not response.ok
        assert response.error.startswith("Data may be incomplete")

    def test_count_calls_v3_count(self):
        self.client.request.return_value = ServiceResponse(
            status=200, res_data={"count": 5}
        )

        self.service.explore_query_count(PROJECT, query="x")

        call = self.client.request.call_args
        assert call.args[0] == (
            "https://explore-service.devsuperannotate.com/api/v3/items/count"
        )
        assert call.kwargs["params"] == {
            "project_id": 1476298,
            "includeFolderNames": True,
        }
        assert call.kwargs["data"] == {"query": "x"}


class ExploreQueryUseCaseTestCase(TestCase):
    def setUp(self):
        self.service_provider = MagicMock()
        self.explore = self.service_provider.explore

    def _use_case(self, cls=ExploreQueryUseCase, folder=ROOT, **kwargs):
        return cls(
            reporter=MagicMock(),
            project=PROJECT,
            folder=folder,
            service_provider=self.service_provider,
            **{"query": None, **kwargs},
        )

    def test_requires_query_or_subset(self):
        response = self._use_case().execute()

        assert str(response.errors) == "Provide 'query' or 'subset'"
        self.explore.explore_query.assert_not_called()

    def test_resolves_the_subset_name(self):
        self.explore.list_subsets.return_value = ServiceResponse(
            status=200, res_data=[SubSetEntity(id=7, name="golden-set")]
        )
        self.explore.explore_query.return_value = _page(1)

        response = self._use_case(subset="golden-set", folder=FOLDER).execute()

        assert not response.errors
        self.explore.explore_query.assert_called_once_with(
            PROJECT, query=None, folder=FOLDER, subset_id=7
        )

    def test_unknown_subset(self):
        self.explore.list_subsets.return_value = ServiceResponse(
            status=200, res_data=[SubSetEntity(id=7, name="other")]
        )

        response = self._use_case(subset="golden-set").execute()

        assert str(response.errors) == "Subset not found"

    def test_root_folder_is_not_sent(self):
        self.explore.explore_query.return_value = _page(1)

        self._use_case(query="x").execute()

        self.explore.explore_query.assert_called_once_with(
            PROJECT, query="x", folder=None
        )

    def test_backend_error_is_reported(self):
        self.explore.explore_query.return_value = ExploreQueryResponse(
            status=400, res_error="Invalid query"
        )

        response = self._use_case(query="x").execute()

        assert response.errors == "Invalid query"

    def test_count(self):
        self.explore.explore_query_count.return_value = ServiceResponse(
            status=200, res_data={"count": 42}
        )

        response = self._use_case(ExploreQueryCountUseCase, query="x").execute()

        assert response.data == 42


class _Recorder:
    def __init__(self):
        self.events = []

    def as_track(self):
        events = self.events

        def _track(
            tracker, user_id, event_name, data, *, client, explicit_credentials=False
        ):
            events.append({"event": event_name, "data": data})

        return _track


@patch.dict(os.environ, {"sa_version": "4.6.2"})
class ExploreTestCase(TestCase):
    def setUp(self):
        self.recorder = _Recorder()
        patcher = patch.object(Tracker, "_track", self.recorder.as_track())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.controller = MagicMock()
        self.controller.get_project_folder.return_value = (PROJECT, ROOT)
        self.controller.explore_query.return_value = [ExploreItem(**ITEM)]
        self.controller.explore_query_count.return_value = 42
        self.explore = Explore(self.controller)

    def test_query_returns_serialized_items_lazily(self):
        result = self.explore.query(project="Project", query="x")
        self.controller.explore_query.assert_not_called()

        assert list(result) == [ExploreItem(**ITEM).model_dump()]
        self.controller.explore_query.assert_called_once_with(PROJECT, ROOT, "x", None)

    def test_count_does_not_fetch_items(self):
        result = self.explore.query(project="Project", query="x", subset="s")

        assert result.count() == 42
        self.controller.explore_query.assert_not_called()
        self.controller.explore_query_count.assert_called_once_with(
            PROJECT, ROOT, "x", "s"
        )

    def test_query_or_subset_is_required(self):
        with self.assertRaisesRegex(AppException, "Provide 'query' or 'subset'"):
            self.explore.query(project="Project")
        self.controller.get_project_folder.assert_not_called()

    def test_events_are_prefixed_with_the_namespace(self):
        self.explore.query(project="Project/folder", query="x").count()
        self.controller.subsets.list.return_value = MagicMock(errors=None, data=[])
        self.explore.get_subsets(project="Project")

        assert [e["event"] for e in self.recorder.events] == [
            "explore.query",
            "explore.query.count",
            "explore.get_subsets",
        ]
        count_data = self.recorder.events[1]["data"]
        assert count_data["query"] == "x"
        assert "_resolved" not in count_data

    def test_client_exposes_one_namespace(self):
        client = object.__new__(SAClient)
        client.controller = self.controller

        assert isinstance(client.explore, Explore)
        assert client.explore is client.explore
        assert client.explore.controller is self.controller


@patch.dict(os.environ, {"sa_version": "4.6.2", "SA_SKIP_METRICS": "true"})
class DeprecationsTestCase(TestCase):
    def setUp(self):
        self.client = object.__new__(SAClient)
        self.client.controller = MagicMock()
        self.client.controller.get_project_folder.return_value = (PROJECT, ROOT)
        self.client.controller.query_items_count.return_value = 3
        self.client.controller.subsets.list.return_value = MagicMock(
            errors=None, data=[]
        )
        self.client.controller.subsets.add_items.return_value = MagicMock(
            errors=None, data={}
        )

    def _warnings(self, call):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            call()
        deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        # Attributed to the caller, not to the SDK's wrappers - Python's default filter
        # only shows a DeprecationWarning attributed to the user's own code.
        assert all(w.filename == __file__ for w in deprecations), [
            w.filename for w in deprecations
        ]
        return [str(w.message) for w in deprecations]

    def test_query(self):
        messages = self._warnings(lambda: self.client.query("Project", query="x"))

        assert len(messages) == 1
        assert "query() will be deprecated and removed in version 4.7.0" in messages[0]
        assert "SAClient.explore.query()" in messages[0]

    def test_query_count(self):
        result = self.client.query("Project", query="x")

        messages = self._warnings(result.count)

        assert messages == [
            "This function query().count() will be deprecated and removed in version 4.7.0\n"
            "Recommended replacement: SAClient.explore.query().count()"
        ]

    def test_get_subsets(self):
        messages = self._warnings(lambda: self.client.get_subsets("Project"))

        assert messages == [
            "This function get_subsets() will be deprecated and removed in version 4.7.0\n"
            "Recommended replacement: SAClient.explore.get_subsets()"
        ]

    def test_add_items_to_subset(self):
        messages = self._warnings(
            lambda: self.client.add_items_to_subset("Project", "s", [{"id": 1}])
        )

        assert messages == [
            "This function add_items_to_subset() will be deprecated and removed in version 4.7.0\n"
            "Recommended replacement: SAClient.explore.add_items_to_subset()"
        ]

    def test_explore_methods_do_not_warn(self):
        explore = Explore(self.client.controller)
        self.client.controller.explore_query_count.return_value = 1

        messages = self._warnings(
            lambda: (
                explore.query("Project", query="x").count(),
                explore.get_subsets("Project"),
                explore.add_items_to_subset("Project", "s", [{"id": 1}]),
            )
        )

        assert messages == []
