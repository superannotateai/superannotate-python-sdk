import sys
from pathlib import Path


LIB_PATH = Path(__file__).parent.parent / "src"
DATA_SET_PATH = Path(__file__).parent / "data_set"
sys.path.insert(0, str(LIB_PATH))

__all__ = [
    "DATA_SET_PATH"
]
