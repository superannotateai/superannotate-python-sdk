import sys
from pathlib import Path


LIB_PATH = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(LIB_PATH))
