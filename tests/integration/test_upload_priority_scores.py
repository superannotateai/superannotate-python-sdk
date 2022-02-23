import os
import src.superannotate as sa
from tests.integration.base import BaseTestCase
from pathlib import Path

class TestUploadPriorityScores(BaseTestCase):
    PROJECT_NAME = "TestUploadPriorityScores"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"

    @property
    def folder_path(self):
        return os.path.join(Path(__file__).parent.parent, self.TEST_FOLDER_PATH)

    def test_upload_priority_scores(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        uploaded, skipped = sa.upload_priority_scores(self.PROJECT_NAME, scores=[{
            "name": "example_image_1.jpg",
            "priority": 1
        }])
        self.assertEqual(len(uploaded), 1)
        self.assertEqual(len(skipped), 0)
        uploaded, skipped = sa.upload_priority_scores(self.PROJECT_NAME, scores=[{
            "name": "non-exist.jpg",
            "priority": 1
        }, {
            "name": "non-exist-2.jpg",
            "priority": 1
        }])
        self.assertEqual(len(uploaded), 0)
        self.assertEqual(len(skipped), 2)
