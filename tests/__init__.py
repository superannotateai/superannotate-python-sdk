import logging
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
        if isinstance(result[key], dict) and isinstance(expected[key], dict):
            compare_result(result[key], expected[key], ignore_keys)
        elif isinstance(result[key], list) and isinstance(expected[key], list):
            for i in range(len(result[key])):
                if isinstance(result[key][i], (dict, list)):
                    compare_result(result[key][i], expected[key][i], ignore_keys)
                else:
                    assert result[key][i] == expected[key][i]
        else:
            try:
                assert result[key] == expected[key]
            except Exception:
                logging.error(f"{result} == {expected}")
                print(key, result[key], expected[key])
    return True


__all__ = ["DATA_SET_PATH", "compare_result"]
