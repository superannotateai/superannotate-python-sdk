# Running the tests

Unit tests need no credentials:

```bash
pytest tests/unit
```

The integration tests talk to a real team, and take their credentials from a `.env` file
in the repository root (copy `.env.example`):

```ini
SA_TOKEN=<API key>
SA_URL=https://api.devsuperannotate.com
# Required for an organization API key, which carries no team of its own.
SA_TEAM_ID=6085
```

```bash
pytest tests/integration
```

The file is read before any test module is imported, so the modules that build their
client at import time with a bare `SAClient()` pick it up. Variables already exported in
the environment win over the file, so CI can provide them without a `.env`; with neither,
the SDK falls back to `~/.superannotate/config.ini`.

Unit tests are hidden from these variables (`tests/unit/conftest.py`) - they assert how
the SDK itself resolves credentials.

## Running as a different token type

What the backend allows depends on the token in the `.env`:

| Token | Acts as | Notes |
| --- | --- | --- |
| Organization API key | the organization | carries no team — `SA_TEAM_ID` is required |
| Team API key | the team, with no user behind it | user-level operations are denied |
| Personal (team-user) API key | the user it was issued for | owner or team admin, per key |
| Legacy team-owner token | the team owner | carries its team in the token |

To run the suite as another type, put that token in the `.env` and run it again. Tests
that only apply to one type declare it and are skipped for the others (see
`tests/env.py`):

```python
from tests import env

@env.requires_organization_token
def test_org_only(sa_client):
    ...
```

## Suites that bring their own token

Some suites describe one specific kind of key rather than the run's own, so they carry
their own variables and are skipped while those are unset:

```ini
# What a project-admin contributor may do (tests/integration/client).
SA_OWNER_PERSONAL_TOKEN=<team owner's personal API key>
SA_PROJECT_ADMIN_TOKEN=<contributor's personal API key, same team>
```

`test_project_admin_token.py` runs its setup as the owner - it creates two projects and
makes the contributor a ProjectAdmin of one of them - and then does everything else as
the contributor, so the role's reach is measured against a project it was never given.
Two of its tests are `xfail`: a project-admin key cannot list team users, and so cannot
add contributors either. Both break inside the SDK, and the reasons on the tests say
where.

`requires_team_token`, `requires_user_token` (personal or legacy) and
`requires_team_scoped_token` (anything but an organization key) work the same way. The
`sa_client` fixture is the client the run authenticates as, and `sa_token_scope` is its
scope.
