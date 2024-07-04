import os
from pathlib import Path

from src.superannotate import SAClient
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestUploadPriorityScores(BaseTestCase):
    PROJECT_NAME = "TestUploadPriorityScores"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"

    @property
    def folder_path(self):
        return os.path.join(Path(__file__).parent.parent, self.TEST_FOLDER_PATH)

    def test_upload_empty_list(self):
        with self.assertLogs("sa", level="INFO") as cm:
            sa.upload_priority_scores(self.PROJECT_NAME, scores=[])
            assert (
                cm.output[0]
                == "INFO:sa:Uploading  priority scores for 0 item(s) to TestUploadPriorityScores."
            )

    def test_upload_priority_scores(self):

        self._attach_items(count=4)
        uploaded, skipped = sa.upload_priority_scores(
            self.PROJECT_NAME, scores=[{"name": "example_image_1.jpg", "priority": 1}]
        )
        self.assertEqual(len(uploaded), 1)
        self.assertEqual(len(skipped), 0)
        uploaded, skipped = sa.upload_priority_scores(
            self.PROJECT_NAME,
            scores=[
                {"name": "non-exist.jpg", "priority": 1},
                {"name": "non-exist-2.jpg", "priority": 1},
            ],
        )
        self.assertEqual(len(uploaded), 0)
        self.assertEqual(len(skipped), 2)
        uploaded, skipped = sa.upload_priority_scores(
            self.PROJECT_NAME,
            scores=[
                {"name": "example_image_3.jpg", "priority": 1.1234567890},
                {"name": "example_image_4.jpg", "priority": 100000000},
            ],
        )
        self.assertEqual(
            sa.get_item_metadata(self.PROJECT_NAME, "example_image_4.jpg")[
                "entropy_value"
            ],
            1000000,
        )
        self.assertEqual(
            sa.get_item_metadata(self.PROJECT_NAME, "example_image_3.jpg")[
                "entropy_value"
            ],
            1.12345,
        )
