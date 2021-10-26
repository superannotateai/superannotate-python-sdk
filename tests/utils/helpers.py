import sys

from io import StringIO
from contextlib import contextmanager


@contextmanager
def catch_prints():
    out = StringIO()
    sys.stdout = out
    yield out