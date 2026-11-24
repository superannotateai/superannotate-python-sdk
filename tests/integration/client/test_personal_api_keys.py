"""List and revoke personal API keys, against the backend.

How it works:
  - Every test class mints its own keys, so nothing depends on keys already in the team,
    and revokes them when it is done.
  - Minting uses a team owner's personal key (the SDK has no call for it). Nothing else does.
  - Listing and revoking use the key under test: a team key and an organization key.
    Both see and may revoke every personal key in the team.

The tests are written once, in ``TestWithTeamKey``, so each one can be run on its own from
the IDE. ``TestWithOrganizationKey`` repeats them all with another key by only saying which
client to use. To cover one more key, subclass it the same way.
"""

import uuid
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from unittest import SkipTest
from unittest import TestCase

from src.superannotate import AppException
from src.superannotate.lib.core.entities.filters import PersonalAPIKeyFilters
from tests import env

#: Every key a run mints starts with this, so a leftover one is easy to spot.
NAME_PREFIX = "sdk-test-personal-key"


def ids(keys) -> list:
    return [key["id"] for key in keys]


def unknown_name() -> str:
    return f"unknown-{uuid.uuid4().hex}"


class TestWithTeamKey(TestCase):
    """Lists and revokes with a team key. Subclasses change the key: see ``build_client``."""

    #: The variables the key under test and the minting key need.
    required_env = (env.SA_TOKEN_ENV, env.SA_PERSONAL_OWNER_TOKEN_ENV)

    @classmethod
    def build_client(cls):
        """The client under test."""
        return env.build_client(env.var(env.SA_TOKEN_ENV))

    # --- setup and cleanup ------------------------------------------------------

    @classmethod
    def setUpClass(cls):
        """Three keys shared by the tests: two active ones and one revoked."""
        missing = env.missing_env_vars(*cls.required_env)
        if missing:
            raise SkipTest(f"needs {', '.join(missing)} in the .env (see tests/env.py)")
        cls.client = cls.build_client()
        cls.minting_client = env.build_client(env.var(env.SA_PERSONAL_OWNER_TOKEN_ENV))
        cls.prefix = f"{NAME_PREFIX}-{uuid.uuid4().hex[:8]}"
        cls.active_1 = cls.shared_key("active-1")
        cls.active_2 = cls.shared_key("active-2")
        cls.revoked = cls.shared_key("revoked")
        cls.client.revoke_personal_api_key(public_id=cls.revoked.public_id)

    @classmethod
    def shared_key(cls, suffix):
        """A key for all the tests, revoked when the class is done."""
        key = cls.mint(f"{cls.prefix}-{suffix}")
        cls.addClassCleanup(cls.revoke_quietly, key.public_id)
        return key

    @classmethod
    def mint(cls, name):
        """A new personal key. The SDK cannot make one, so the service does."""
        work_management = cls.minting_client.controller.service_provider.work_management
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        key = work_management.create_personal_api_key(
            name=name,
            expires_at=expires_at.isoformat(timespec="milliseconds").replace(
                "+00:00", "Z"
            ),
        )
        return key

    @classmethod
    def rotate(cls, key):
        """Rotates a key: the old one keeps its public id, the new one takes it too."""
        work_management = cls.minting_client.controller.service_provider.work_management
        now = datetime.now(timezone.utc)
        return work_management.rotate_personal_api_key(
            key_id=key.id,
            overlap_end_at=cls.wire_date(now + timedelta(days=7)),
            expires_at=cls.wire_date(now + timedelta(days=30)),
        )

    @staticmethod
    def wire_date(value):
        return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    @classmethod
    def revoke_quietly(cls, public_id):
        try:
            cls.client.revoke_personal_api_key(public_id=public_id)
        except AppException:
            pass  # a test already revoked it

    def new_key(self):
        """A key for a single test, revoked after it. `mine()` does not list it."""
        key = self.mint(f"{NAME_PREFIX}-temp-{uuid.uuid4().hex[:8]}")
        self.addCleanup(self.revoke_quietly, key.public_id)
        return key

    def mine(self, **filters):
        """Only the three shared keys, newest first."""
        return self.client.list_personal_api_keys(name__starts=self.prefix, **filters)

    # --- list: results ----------------------------------------------------------

    def test_list_returns_the_keys_newest_first(self):
        assert ids(self.mine()) == [
            self.revoked.id,
            self.active_2.id,
            self.active_1.id,
        ]

    def test_list_returns_what_was_minted(self):
        [listed] = self.client.list_personal_api_keys(id=self.active_1.id)

        assert listed["name"] == self.active_1.name
        assert listed["public_id"] == self.active_1.public_id
        assert listed["scope"] == self.active_1.scope
        assert listed["status"] == "ACTIVE"

    def test_list_never_returns_the_secret(self):
        for key in self.client.list_personal_api_keys():
            assert "api_key" not in key

    def test_list_reads_every_page(self):
        from lib.core.jsx_conditions import EmptyQuery

        work_management = self.client.controller.service_provider.work_management

        paged = work_management.list_personal_api_keys(EmptyQuery(), chunk_size=1)

        assert sorted(key.id for key in paged.data) == sorted(
            ids(self.client.list_personal_api_keys())
        )

    # --- list: filters ----------------------------------------------------------

    def test_filters(self):
        """Every filter, alone and combined, with every kind of collection."""
        a, b, r = self.active_1, self.active_2, self.revoked
        # (filters, the keys they must return, newest first). Each also gets
        # name__starts=prefix, so only the three shared keys can be returned.
        cases = [
            ({"id": a.id}, [a]),
            ({"id__in": [a.id, r.id]}, [r, a]),
            ({"name": a.name}, [a]),
            ({"name__in": [a.name, r.name, unknown_name()]}, [r, a]),
            ({"name__contains": "-active-"}, [b, a]),
            ({"name__starts": f"{self.prefix}-active"}, [b, a]),
            ({"name__ends": "-revoked"}, [r]),
            ({"status": "Active"}, [b, a]),
            ({"status": "ACTIVE"}, [b, a]),
            ({"status": "active"}, [b, a]),
            ({"status": "Rotating"}, []),
            ({"status__ne": "Active"}, [r]),
            ({"status__in": ["Revoked", "Rotating"]}, [r]),
            ({"status__notin": ["Active"]}, [r]),
            ({"status__notin": ["Active", "Revoked"]}, []),
            ({"status": "Revoked", "name__ends": "-revoked"}, [r]),
            ({"status": "Active", "name__ends": "-revoked"}, []),
            ({"name": unknown_name()}, []),
        ]
        # A filter added to PersonalAPIKeyFilters without a case here fails this.
        used = {name for filters, _ in cases for name in filters}
        assert used == set(PersonalAPIKeyFilters.__annotations__)

        for filters, expected in cases:
            # List values may be given as any collection.
            for collection in (list, tuple, set):
                given = {
                    name: collection(value) if isinstance(value, list) else value
                    for name, value in filters.items()
                }
                with self.subTest(filters=filters, collection=collection.__name__):
                    found = self.client.list_personal_api_keys(
                        **{"name__starts": self.prefix, **given}
                    )

                    assert ids(found) == [key.id for key in expected]

        with self.assertRaisesRegex(AppException, "Invalid status filter: Rotated"):
            self.client.list_personal_api_keys(status="Rotated")
        with self.assertRaisesRegex(AppException, "Invalid filter param provided."):
            self.client.list_personal_api_keys(scope_type="teamuser")

    # --- revoke -----------------------------------------------------------------

    def test_revoke_marks_the_key_revoked(self):
        key = self.new_key()

        self.client.revoke_personal_api_key(public_id=key.public_id)

        [listed] = self.client.list_personal_api_keys(id=key.id)
        assert listed["status"] == "REVOKED"
        assert listed["revokedAt"]

    def test_revoke_logs_the_public_id(self):
        key = self.new_key()

        with self.assertLogs("sa", level="INFO") as logs:
            self.client.revoke_personal_api_key(public_id=key.public_id)

        assert any(
            f"Successfully revoked API key: {key.public_id}." in line
            for line in logs.output
        )

    def test_revoke_by_id_marks_the_key_revoked(self):
        key = self.new_key()

        self.client.revoke_personal_api_key(api_key_id=key.id)

        [listed] = self.client.list_personal_api_keys(id=key.id)
        assert listed["status"] == "REVOKED"

    def test_revoke_by_id_revokes_only_that_key(self):
        old = self.new_key()
        new = self.rotate(old)

        self.client.revoke_personal_api_key(api_key_id=old.id)

        [old_listed] = self.client.list_personal_api_keys(id=old.id)
        [new_listed] = self.client.list_personal_api_keys(id=new.id)
        assert old_listed["status"] == "REVOKED"
        assert new_listed["status"] == "ACTIVE"

    def test_revoke_by_public_id_revokes_the_active_key_and_its_rotations(self):
        keys = [self.new_key()]
        for _ in range(3):
            keys.append(self.rotate(keys[-1]))

        self.client.revoke_personal_api_key(public_id=keys[0].public_id)

        key_ids = [key.id for key in keys]
        listed = self.client.list_personal_api_keys(id__in=key_ids)
        assert sorted(ids(listed)) == sorted(key_ids)
        assert {key["status"] for key in listed} == {"REVOKED"}

    def test_revoke_needs_a_public_id_or_an_id_but_not_both(self):
        key = self.new_key()

        for kwargs in ({}, {"public_id": key.public_id, "api_key_id": key.id}):
            with self.assertRaisesRegex(
                AppException, "Must provide either public_id or api_key_id."
            ):
                self.client.revoke_personal_api_key(**kwargs)
        [listed] = self.client.list_personal_api_keys(id=key.id)
        assert listed["status"] == "ACTIVE"

    def test_revoke_twice_fails(self):
        key = self.new_key()
        self.client.revoke_personal_api_key(public_id=key.public_id)

        with self.assertRaisesRegex(AppException, "already revoked or expired"):
            self.client.revoke_personal_api_key(public_id=key.public_id)

    def test_revoke_a_revoked_key_fails(self):
        with self.assertRaisesRegex(AppException, "already revoked or expired"):
            self.client.revoke_personal_api_key(public_id=self.revoked.public_id)

    def test_revoke_an_unknown_key_fails(self):
        with self.assertRaisesRegex(AppException, "API key not found"):
            self.client.revoke_personal_api_key(public_id=unknown_name())
        with self.assertRaisesRegex(AppException, "API key not found"):
            self.client.revoke_personal_api_key(api_key_id=2**31 - 1)


class TestWithOrganizationKey(TestWithTeamKey):
    required_env = (
        env.SA_ORGANIZATION_TOKEN_ENV,
        env.SA_ORGANIZATION_TEAM_ID_ENV,
        env.SA_PERSONAL_OWNER_TOKEN_ENV,
    )

    @classmethod
    def build_client(cls):
        return env.build_client(
            env.var(env.SA_ORGANIZATION_TOKEN_ENV),
            team_id=int(env.var(env.SA_ORGANIZATION_TEAM_ID_ENV)),
        )
