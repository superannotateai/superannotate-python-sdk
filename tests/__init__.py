import os
import sys
from pathlib import Path

os.environ.update({"SA_VERSION_CHECK": "False"})

LIB_PATH = Path(__file__).parent.parent / "src"
DATA_SET_PATH = Path(__file__).parent / "data_set"
sys.path.insert(0, str(LIB_PATH))

__all__ = ["DATA_SET_PATH"]

# from src.superannotate.lib.core import setup_logging
#
# logger = get_default_logger()
# logger.setLevel("DEBUG")
