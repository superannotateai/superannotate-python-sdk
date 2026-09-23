"""Minting, rotating, listing and revoking a team API key, against the backend.

Every test builds its client from the organization key named in the .env, plus the
team id that key can reach - what generate and rotate require - and is skipped while
either is unset (see tests/env.py).

Keys are real: each one a test mints is named after this run and revoked when the test
finishes, so a run leaves the team as it found it.
"""

import contextlib
import uuid
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from unittest import TestCase

import pytest
from src.superannotate import AppException
from src.superannotate.lib.core.entities.context import TokenScope
from tests import env

#: Every key a run mints carries this prefix, so one left behind by a run that died
#: mid-test is recognisable at a glance.
NAME_PREFIX = "sdk-test-key"
#: The statuses a key can still be revoked in, and so the ones cleanup looks for.
LIVE = ["Active", "Rotating"]


def as_datetime(value: str) -> datetime:
    """A date the backend reports, as an aware datetime."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def days_from_now(value: str) -> float:
    return (as_datetime(value) - datetime.now(timezone.utc)).total_seconds() / 86400


@env.requires_env_vars(env.SA_ORGANIZATION_TOKEN_ENV, env.SA_ORGANIZATION_TEAM_ID_ENV)
class TeamAPIKeyTestCase(TestCase):
    """A team-scoped client on an organization key, and cleanup after each test."""

    @classmethod
    def setUpClass(cls):
        cls.team_id = int(env.var(env.SA_ORGANIZATION_TEAM_ID_ENV))
        cls.client = env.build_client(
            env.var(env.SA_ORGANIZATION_TOKEN_ENV), team_id=cls.team_id
        )

    def setUp(self):
        #: The names this test minted. A rotation reuses the name of the key it
        #: rotates, so the pair it leaves behind is covered by the same entry.
        self.minted = []

    def tearDown(self):
        for key in self.client.list_team_api_keys(status__in=LIVE, nane__startswith=NAME_PREFIX).keys():
            self.minted.append(key)
            if key["name"] in self.minted:
                with contextlib.suppress(AppException):
                    self.client.revoke_team_api_key(public_id=key["public_id"])

    def generate(self, name: str = None, **kwargs) -> dict:
        """A key of this run's own, revoked when the test ends."""
        name = name if name is not None else f"{NAME_PREFIX}-{uuid.uuid4().hex[:8]}"
        self.minted.append(name)
        return self.client.generate_team_api_key(name=name, **kwargs)

    def listed(self, public_id: str) -> dict:
        """One key as the backend now reports it, by its public id."""
        keys = self.client.list_team_api_keys()
        key = next((k for k in keys if k["public_id"] == public_id), None)
        assert key is not None, f"{public_id} is not among the team's keys"
        return key


class TestGenerateTeamAPIKey(TeamAPIKeyTestCase):
    def test_a_generated_key_is_active_and_carries_its_secret(self):
        generated = self.generate()

        assert generated["status"] == "ACTIVE"
        assert generated["scope"] == {"team_id": self.team_id}
        assert generated["name"] in self.minted
        assert generated["public_id"]
        # The secret is reported once, here, and never again.
        assert generated["api_key"].startswith("sa_")

    def test_a_key_lives_a_year_unless_told_otherwise(self):
        generated = self.generate()

        assert 364 < days_from_now(generated["expiresAt"]) <= 365

    def test_expires_in_takes_days_a_duration_or_a_date(self):
        by_days = self.generate(expires_in=30)
        by_duration = self.generate(expires_in=timedelta(days=60))
        expiry = datetime.now() + timedelta(days=90)
        by_date = self.generate(expires_in=expiry)

        assert 29 < days_from_now(by_days["expiresAt"]) <= 30
        assert 59 < days_from_now(by_duration["expiresAt"]) <= 60
        # A date is the expiry itself, to the millisecond the wire format carries.
        assert as_datetime(by_date["expiresAt"]) == expiry.astimezone(
            timezone.utc
        ).replace(microsecond=expiry.microsecond // 1000 * 1000)

    def test_expires_in_takes_nothing_else(self):
        # 30.5 is no number of days, and must not be read as 30.5 *seconds*.
        for invalid in (30.5, 30.0, "30", "2027-01-01", None, True):
            with pytest.raises(AppException):
                self.generate(expires_in=invalid)

    def test_a_blank_name_is_rejected(self):
        for blank in ("", "   "):
            with self.assertRaisesRegex(AppException, "Name cannot be empty"):
                self.generate(name=blank)

    def test_a_duplicate_name_is_refused_by_the_backend(self):
        taken = self.generate()["name"]

        # The SDK does not check this one: the backend owns the rule, and says so.
        with pytest.raises(AppException):
            self.generate(name=taken)

    def test_the_generated_key_authenticates_as_its_team(self):
        generated = self.generate()

        client = env.build_client(generated["api_key"])

        assert client.controller.token_context.scope == TokenScope.TEAM
        assert client.controller.team_id == self.team_id


class TestListTeamAPIKeys(TeamAPIKeyTestCase):
    def test_a_generated_key_is_listed_first(self):
        generated = self.generate()

        keys = self.client.list_team_api_keys()

        assert keys[0]["public_id"] == generated["public_id"]
        # Newest first, all the way down.
        assert [k["id"] for k in keys] == sorted((k["id"] for k in keys), reverse=True)

    def test_a_listed_key_carries_no_secret(self):
        generated = self.generate()

        assert "api_key" not in self.listed(generated["public_id"])

    def test_filtering_by_name_and_status(self):
        generated = self.generate()

        by_name = self.client.list_team_api_keys(name=generated["name"])
        by_status = self.client.list_team_api_keys(
            name=generated["name"], status__in=LIVE
        )
        excluded = self.client.list_team_api_keys(
            name=generated["name"], status__notin=LIVE
        )

        assert [k["public_id"] for k in by_name] == [generated["public_id"]]
        assert [k["public_id"] for k in by_status] == [generated["public_id"]]
        assert excluded == []

    def test_filtering_by_a_fragment_of_the_name(self):
        generated = self.generate()

        assert generated["public_id"] in [
            k["public_id"]
            for k in self.client.list_team_api_keys(name__starts=NAME_PREFIX)
        ]

    def test_nothing_matching_is_an_empty_list(self):
        assert self.client.list_team_api_keys(name=f"absent-{uuid.uuid4().hex}") == []

    def test_an_unknown_status_is_rejected(self):
        with self.assertRaisesRegex(AppException, "Invalid status filter: Rotated"):
            self.client.list_team_api_keys(status="Rotated")

    def test_an_unsupported_filter_is_rejected(self):
        with self.assertRaisesRegex(AppException, "Invalid filter param provided."):
            self.client.list_team_api_keys(scope_type="team")


class TestRotateTeamAPIKey(TeamAPIKeyTestCase):
    def test_rotating_mints_a_new_key_and_leaves_the_old_one_rotating(self):
        old = self.generate()

        new = self.client.rotate_team_api_key(
            name=old["name"], overlap=1, expires_in=90
        )

        assert new["public_id"] != old["public_id"]
        assert new["status"] == "ACTIVE"
        assert new["api_key"].startswith("sa_")
        assert 89 < days_from_now(new["expiresAt"]) <= 90
        # The key that was rotated stays valid for the overlap window.
        rotated = self.listed(old["public_id"])
        assert rotated["status"] == "ROTATING"
        assert rotated["overlapEndAt"]

    def test_a_key_is_rotated_by_public_id_too(self):
        old = self.generate()

        new = self.client.rotate_team_api_key(name=old["public_id"])

        assert new["public_id"] != old["public_id"]
        assert self.listed(old["public_id"])["status"] == "ROTATING"

    def test_the_new_key_authenticates_while_the_old_one_still_can(self):
        old = self.generate()

        new = self.client.rotate_team_api_key(name=old["name"], overlap=1)

        assert env.build_client(new["api_key"]).controller.team_id == self.team_id
        assert env.build_client(old["api_key"]).controller.team_id == self.team_id

    def test_an_overlap_longer_than_the_new_expiry_is_rejected(self):
        old = self.generate()

        with self.assertRaisesRegex(
            AppException,
            "The overlap period cannot be longer than the new key expiration",
        ):
            self.client.rotate_team_api_key(name=old["name"], overlap=30, expires_in=7)

        assert self.listed(old["public_id"])["status"] == "ACTIVE"

    def test_an_overlap_outside_the_offered_windows_is_rejected(self):
        old = self.generate()

        for invalid in (3, 0, "immediately"):
            with pytest.raises(AppException):
                self.client.rotate_team_api_key(name=old["name"], overlap=invalid)

        assert self.listed(old["public_id"])["status"] == "ACTIVE"

    def test_an_unknown_key_cannot_be_rotated(self):
        with self.assertRaisesRegex(AppException, "API key not found"):
            self.client.rotate_team_api_key(name=f"absent-{uuid.uuid4().hex}")


class TestRevokeTeamAPIKey(TeamAPIKeyTestCase):
    def test_revoking_marks_the_key_revoked(self):
        generated = self.generate()

        assert self.client.revoke_team_api_key(public_id=generated["public_id"]) is None

        revoked = self.listed(generated["public_id"])
        assert revoked["status"] == "REVOKED"
        assert revoked["revokedAt"]

    def test_a_rotating_key_can_be_revoked(self):
        old = self.generate()
        self.client.rotate_team_api_key(name=old["name"], overlap=7)

        self.client.revoke_team_api_key(public_id=old["public_id"])

        assert self.listed(old["public_id"])["status"] == "REVOKED"

    def test_a_revoked_key_cannot_be_revoked_again(self):
        generated = self.generate()
        self.client.revoke_team_api_key(public_id=generated["public_id"])

        with self.assertRaisesRegex(
            AppException, "This key is already revoked or expired"
        ):
            self.client.revoke_team_api_key(public_id=generated["public_id"])

    def test_a_revoked_key_no_longer_authenticates(self):
        generated = self.generate()
        self.client.revoke_team_api_key(public_id=generated["public_id"])

        with pytest.raises(AppException):
            env.build_client(generated["api_key"])

    def test_an_unknown_public_id_cannot_be_revoked(self):
        with self.assertRaisesRegex(AppException, "API key not found"):
            self.client.revoke_team_api_key(public_id=f"absent-{uuid.uuid4().hex[:16]}")
