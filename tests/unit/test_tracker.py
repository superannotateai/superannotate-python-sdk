"""The telemetry decorator every public SDK method is wrapped in.

Exercised against throwaway Trackable classes rather than SAClient, so what is under
test is the decorator itself: which event it reports, what lands in the payload, and
what it must not do. Nothing here touches the network - Tracker._track is patched, and
it would refuse to send from a test run anyway.
"""

import os
from unittest import TestCase
from unittest.mock import patch

from superannotate.lib.app.interface.base_interface import Tracker
from superannotate.lib.app.interface.base_interface import TrackableMeta


class _Recorder:
    """Collects what Tracker._track was handed, in place of sending it."""

    def __init__(self):
        self.events = []

    def as_track(self):
        """A stand-in for Tracker._track.

        A plain function, so it binds as a method - an instance with __call__ would
        not, and the resulting TypeError would be swallowed along with everything
        else _track_method guards against.
        """
        events = self.events

        def _track(
            tracker, user_id, event_name, data, *, client, explicit_credentials=False
        ):
            events.append({"user_id": user_id, "event": event_name, "data": data})

        return _track

    @property
    def events_named(self):
        return [event["event"] for event in self.events]

    @property
    def last(self):
        return self.events[-1]


class _Subject(metaclass=TrackableMeta):
    def __init__(self, controller=None):
        self.controller = controller

    def work(self, project, item_name=None, count=None, options=None):
        return "ok"

    def blows_up(self):
        raise ValueError("nope")

    def interrupted(self):
        raise KeyboardInterrupt("ctrl-c")

    def _private(self):  # not wrapped: TrackableMeta skips underscored names
        return "quiet"


@patch.dict(os.environ, {"sa_version": "4.6.0"})
class TrackerTestCase(TestCase):
    def setUp(self):
        self.recorder = _Recorder()
        patcher = patch.object(Tracker, "_track", self.recorder.as_track())
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_reports_the_method_name_and_the_calling_class(self):
        _Subject().work(project="p")

        assert self.recorder.last["event"] == "work"
        assert self.recorder.last["data"]["Class"] == "_Subject"

    def test_underscored_methods_are_not_tracked(self):
        _Subject()._private()

        assert self.recorder.events_named == ["__init__"]

    def test_a_failing_call_is_reported_as_a_failure_and_still_raises(self):
        with self.assertRaises(ValueError):
            _Subject().blows_up()

        assert self.recorder.last["event"] == "blows_up"
        assert self.recorder.last["data"]["Success"] is False

    def test_an_interrupted_call_is_not_reported_as_a_success(self):
        # __call__ catches BaseException for this: with `except Exception` a
        # KeyboardInterrupt skipped the failure flag and the call was logged as done.
        with self.assertRaises(KeyboardInterrupt):
            _Subject().interrupted()

        assert self.recorder.last["data"]["Success"] is False

    def test_the_original_traceback_is_not_reframed(self):
        # A bare `raise` keeps this decorator out of the traceback the caller sees.
        try:
            _Subject().blows_up()
        except ValueError as e:
            frames = []
            tb = e.__traceback__
            while tb is not None:
                frames.append(tb.tb_frame.f_code.co_name)
                tb = tb.tb_next

        assert frames[-1] == "blows_up"


class SkipMetricsTestCase(TestCase):
    def setUp(self):
        self.recorder = _Recorder()
        patcher = patch.object(Tracker, "_track", self.recorder.as_track())
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_nothing_is_gathered_once_metrics_are_turned_off(self):
        # Read per call, not at import: a Tracker is built while its class is being
        # created, so a value captured then would ignore anything set afterwards.
        with patch.dict(os.environ, {"SA_SKIP_METRICS": "true"}):
            _Subject().work(project="p")

        assert self.recorder.events == []

    def test_metrics_resume_when_it_is_turned_back_on(self):
        with patch.dict(os.environ, {"SA_SKIP_METRICS": "false"}):
            _Subject().work(project="p")

        assert self.recorder.events_named == ["__init__", "work"]


class PayloadTestCase(TestCase):
    """What reaches the payload, and what is held back."""

    def test_credentials_are_reduced_to_whether_they_were_given(self):
        _, properties = Tracker.default_parser(
            "__init__", {"self": object(), "token": "sa_secret", "config_path": None}
        )

        assert properties["sa_token"] == "True"
        assert "token" not in properties
        assert properties["config_path"] == "False"

    def test_a_project_path_is_split_into_project_and_folder(self):
        _, properties = Tracker.default_parser("work", {"project": "Proj/batch1"})

        assert properties["project_name"] == "Proj"
        assert properties["folder_name"] == "batch1"

    def test_containers_are_reduced_to_their_shape(self):
        _, properties = Tracker.default_parser(
            "work",
            {
                "options": {"a": 1, "b": 2},
                "count": 3,
                "names": ["x", "y"],
                "flag": True,
            },
        )

        # A dict contributes its keys, a sized value its length - not the contents.
        assert properties["options"] == ["a", "b"]
        assert properties["names"] == 2
        assert properties["count"] == 3
        assert properties["flag"] is True

    def test_defaults_are_filled_in_for_arguments_the_caller_omitted(self):
        arguments = Tracker.extract_arguments(
            _Subject.work.__wrapped__, _Subject(), project="p"
        )

        assert arguments["item_name"] is None
        assert arguments["count"] is None


class DefaultPayloadTestCase(TestCase):
    """The per-event envelope, which used to be cached."""

    def _payload(self):
        return Tracker.get_default_payload("Team A", "a@b.com", "Team API Key")

    def test_carries_the_identity_of_the_client(self):
        with patch.dict(os.environ, {"sa_version": "4.6.0"}):
            payload = self._payload()

        assert payload["Team"] == "Team A"
        assert payload["User Email"] == "a@b.com"
        assert payload["Auth Type"] == "Team API Key"
        assert payload["Version"] == "4.6.0"
        assert payload["SDK"] is True

    def test_each_event_gets_its_own_dict(self):
        # It was lru_cached, so every event shared one dict: a caller mutating the
        # payload it was handed corrupted every later event.
        with patch.dict(os.environ, {"sa_version": "4.6.0"}):
            first = self._payload()
            first["Team"] = "MUTATED"

            assert self._payload()["Team"] == "Team A"

    def test_the_environment_is_read_per_event(self):
        # Caching also froze SA_ENV and sa_version as they were on the first call.
        with patch.dict(os.environ, {"sa_version": "4.6.0"}):
            assert self._payload()["Env"] == "N/A"
            with patch.dict(os.environ, {"SA_ENV": "staging"}):
                assert self._payload()["Env"] == "staging"


class TrackableMetaTestCase(TestCase):
    def test_a_subclass_need_not_define_its_own_init(self):
        # attrs["__init__"] used to be read unconditionally, so a Trackable subclass
        # without one raised KeyError while the class was being created.
        class Inheriting(_Subject):
            def extra(self):
                return "ok"

        assert Inheriting().extra() == "ok"

    def test_the_wrapped_method_keeps_its_identity(self):
        assert _Subject.work.__name__ == "work"
        assert _Subject().work.__name__ == "work"
