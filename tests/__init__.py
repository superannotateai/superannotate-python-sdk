import os
import sys
from pathlib import Path

os.environ.update({"SA_VERSION_CHECK": "False"})

LIB_PATH = Path(__file__).parent.parent / "src"
DATA_SET_PATH = Path(__file__).parent / "data_set"
sys.path.insert(0, str(LIB_PATH))


def compare_result(result: dict, expected: dict, ignore_keys: set = None):
    for key in result:
        if ignore_keys and key in ignore_keys:
            continue
        assert result[key] == expected[key]
    return True


__all__ = ["DATA_SET_PATH", "compare_result"]
