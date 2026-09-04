"""Unit tests read no credentials.

The suite loads the project's ``.env`` (``tests/conftest.py``) for the sake of modules
that build a client at import time. The tests here assert how the SDK picks up
credentials, so they must not see whatever happens to be in the developer's ``.env`` -
neither through the environment nor through a ``load_dotenv()`` of the code under test.
"""

import pytest
from tests import env

CREDENTIAL_VARS = (
    "SA_TOKEN",
    "SA_URL",
    "SA_TEAM_ID",
    "SA_SSL",
    env.OWNER_PERSONAL_TOKEN_ENV,
    env.SA_CONTRIBUTOR_TOKEN_ENV,
    env.SA_ORGANIZATION_TOKEN_ENV,
    env.SA_ORGANIZATION_TEAM_ID_ENV,
)


@pytest.fixture(autouse=True)
def hide_credentials(tmp_path_factory):
    overrides = {var: None for var in CREDENTIAL_VARS}
    # A .env path that does not exist, so re-reading the file cannot bring them back.
    overrides[env.ENV_FILE_ENV] = str(tmp_path_factory.mktemp("no-dotenv") / ".env")
    with env.environ(**overrides):
        yield
