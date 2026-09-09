import os

import pytest
from tests import env

# Read before any test module is imported, so a module that builds its client at import
# time authenticates with the project's .env rather than falling back to the SDK's own
# ~/.superannotate/config.ini.
env.load_dotenv()


@pytest.fixture(autouse=True)
def tests_setup():
    os.environ.update({"SA_TESTING": "True", "SA_VERSION_CHECK": "False"})


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "requires_token_scope(*scopes): run only when the .env token has one of these "
        "scopes (see tests/env.py).",
    )


def pytest_runtest_setup(item):
    # Resolved here rather than at import time: reading the token's scope costs a request
    # to the backend, so only a run that actually reaches such a test pays for it.
    for marker in item.iter_markers(name="requires_token_scope"):
        scope = env.token_scope()
        if scope not in marker.args:
            pytest.skip(
                f"requires a token of scope {' or '.join(marker.args)}; "
                f"the configured one is {scope}"
            )


@pytest.fixture(scope="session")
def sa_client():
    """The client the suite runs as, built from the .env credentials."""
    return env.get_client()


@pytest.fixture(scope="session")
def sa_token_scope():
    """The scope of the token the suite runs with."""
    return env.token_scope()
