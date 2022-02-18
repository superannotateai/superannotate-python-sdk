import os
import pytest


@pytest.fixture(autouse=True)
def tests_setup():
    os.environ.update({"SA_TESTING": "True"})
