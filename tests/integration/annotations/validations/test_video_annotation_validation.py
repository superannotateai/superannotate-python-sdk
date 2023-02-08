import json
import os
from unittest import TestCase

from src.superannotate import SAClient
from tests import DATA_SET_PATH

sa = SAClient()


class TestVectorValidators(TestCase):
    PROJECT_NAME = "video annotation upload with ree text and numeric"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Video"
    ANNOTATIONS_PATH = "invalid_annotations/video.mp4.json"

    # @patch('builtins.print')
    def test_free_text_numeric_invalid(self):
        json_data = json.load(open(os.path.join(DATA_SET_PATH, self.ANNOTATIONS_PATH)))
        is_valid = sa.validate_annotations("Video", json_data)
        assert not is_valid
