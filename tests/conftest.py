import pytest
from tests import env

# Read before any test module is imported, so a module that builds its client at import
# time authenticates with the project's .env rather than falling back to the SDK's own
# ~/.superannotate/config.ini.
env.load_dotenv()


@pytest.fixture(scope="session")
def sa_client():
    """The client the suite runs as, built from the .env credentials."""
    return env.get_client()
