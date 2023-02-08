import sys
from contextlib import contextmanager
from io import StringIO


@contextmanager
def catch_prints():
    out = StringIO()
    sys.stdout = out
    yield out
