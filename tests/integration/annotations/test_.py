import os

import tempfile
from pathlib import Path
import json
import sys
import logging
logging.basicConfig(level=logging.DEBUG)


LIB_PATH = Path(__file__).parent.parent.parent.parent / "src"
print(LIB_PATH)
sys.path.insert(0, str(LIB_PATH))
sys.path.append(str( Path(__file__).parent.parent.parent.parent))
from src.superannotate import SAClient

# # def test_():
# os.environ.update(
#     {
#         "SA_VERSION_CHECK": "False",
#         "SA_URL": "https://api.devsuperannotate.com",
#         "SA_TOKEN": "b0677090e55b8fe5d7448e459a13b0aa3d0fdf8be71fb64c3f10cdde129703de1300ea0a613a7909t=8084"
#     }
# )
def test_():
    sa = SAClient()
    VECTOR_JSON = "example_image_1.jpg___objects.json"
    with tempfile.TemporaryDirectory() as tmpdir_name:
        with open(f"{tmpdir_name}/{VECTOR_JSON}", "w") as f:
            json.dump([{"metadata": {"name": "name"}, "instances": []}], f)
        print(sa.upload_annotations_from_folder_to_project("testo", f"{tmpdir_name}"))
    # sa.get_annotations("50k Large Data")



