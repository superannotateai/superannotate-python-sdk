"""Integration tests, run against a real team.

The credentials come from the project's ``.env`` file (see ``tests/env.py``), which
``tests/conftest.py`` reads into the environment before any of these modules is imported -
they build their client at import time with a bare ``SAClient()``.
"""
