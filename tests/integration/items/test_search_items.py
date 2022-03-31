import os
from pathlib import Path

import src.superannotate as sa
import src.superannotate.lib.core as constances
from tests.integration.base import BaseTestCase
from tests.integration.items import IMAGE_EXPECTED_KEYS


class TestSearchItems(BaseTestCase):
    PROJECT_NAME = "TestSearchItems"
    PROJECT_DESCRIPTION = "TestSearchItems"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    IMAGE1_NAME = "example_image_1.jpg"
    IMAGE2_NAME = "example_image_2.jpg"

    @property
    def folder_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.TEST_FOLDER_PATH)

    def test_get_item_metadata(self):
        sa.upload_images_from_folder_to_project(
            self.PROJECT_NAME, self.folder_path, annotation_status="InProgress"
        )
        items = sa.search_items(self.PROJECT_NAME)
        assert list(items[0].keys()).sort() == IMAGE_EXPECTED_KEYS.sort()
        assert len(items) == 4
        assert len(sa.search_items(self.PROJECT_NAME, qa_email="justaemail@google.com")) == 0
        assert len(sa.search_items(self.PROJECT_NAME, annotator_email="justaemail@google.com")) == 0
        assert len(sa.search_items(self.PROJECT_NAME, name_contains="1.jp")) == 1
        assert len(sa.search_items(self.PROJECT_NAME, name_contains=".jpg")) == 4
        assert len(sa.search_items(self.PROJECT_NAME, recursive=True)) == 4
        sa.set_image_annotation_status(self.PROJECT_NAME, self.IMAGE1_NAME, constances.AnnotationStatus.COMPLETED.name)
        sa.set_image_annotation_status(self.PROJECT_NAME, self.IMAGE2_NAME, constances.AnnotationStatus.COMPLETED.name)
        assert len(
            sa.search_items(self.PROJECT_NAME, annotation_status=constances.AnnotationStatus.COMPLETED.name)
        ) == 2
