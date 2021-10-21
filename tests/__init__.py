import sys
from pathlib import Path


lib_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(lib_path))
