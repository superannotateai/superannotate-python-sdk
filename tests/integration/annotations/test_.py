import os

from src.superannotate import SAClient
from pathlib import Path
import sys
import logging
logging.basicConfig(level=logging.DEBUG)


LIB_PATH = Path(__file__).parent.parent.parent.parent / "src"
print(LIB_PATH)
sys.path.insert(0, str(LIB_PATH))
sys.path.append(str( Path(__file__).parent.parent.parent.parent))
def test_():
    os.environ.update(
        {
            "SA_VERSION_CHECK": "False",
            "SA_URL": "https://api.devsuperannotate.com",
            "SA_TOKEN": "b0677090e55b8fe5d7448e459a13b0aa3d0fdf8be71fb64c3f10cdde129703de1300ea0a613a7909t=8084"
        }
    )
    sa = SAClient()
    sa.get_annotations("50k Large Data")
