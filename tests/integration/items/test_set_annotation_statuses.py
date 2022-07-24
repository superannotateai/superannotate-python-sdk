import os
from pathlib import Path

from src.superannotate import SAClient
sa = SAClient()
from src.superannotate import AppException
from src.superannotate.lib.core.usecases import SetAnnotationStatues
from tests.integration.base import BaseTestCase


class TestSetAnnotationStatuses(BaseTestCase):
    PROJECT_NAME = "TestSetAnnotationStatuses"
    PROJECT_DESCRIPTION = "TestSetAnnotationStatuses"
    PROJECT_TYPE = "Vector"
    FOLDER_NAME = "test_folder"
    CSV_PATH = "data_set/attach_urls.csv"
    EXAMPLE_IMAGE_1 = "6022a74d5384c50017c366b3"
    EXAMPLE_IMAGE_2 = "6022a74b5384c50017c366ad"
    ATTACHMENT_LIST = [
        {
            "url": "https://drive.google.com/uc?export=download&id=1vwfCpTzcjxoEA4hhDxqapPOVvLVeS7ZS",
            "name": "6022a74d5384c50017c366b3"
        },
        {
            "url": "https://drive.google.com/uc?export=download&id=1geS2YtQiTYuiduEirKVYxBujHJaIWA3V",
            "name": "6022a74b5384c50017c366ad"
        },
        {
            "url": "1SfGcn9hdkVM35ZP0S93eStsE7Ti4GtHU",
            "path": "123"
        },
        {
            "url": "https://drive.google.com/uc?export=download&id=1geS2YtQiTYuiduEirKVYxBujHJaIWA3V",
            "name": "6022a74b5384c50017c366ad"
        },
    ]

    @property
    def scv_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.CSV_PATH)

    def test_image_annotation_status(self):
        sa.attach_items(
            self.PROJECT_NAME, self.ATTACHMENT_LIST, annotation_status="InProgress"
        )

        sa.set_annotation_statuses(
            self.PROJECT_NAME, "QualityCheck",
        )
        for image in sa.search_items(self.PROJECT_NAME):
            self.assertEqual(image["annotation_status"], "QualityCheck")

    def test_image_annotation_status_via_names(self):
        sa.attach_items(
            self.PROJECT_NAME, self.ATTACHMENT_LIST, annotation_status="InProgress"
        )

        sa.set_annotation_statuses(
            self.PROJECT_NAME, "QualityCheck", [self.EXAMPLE_IMAGE_1, self.EXAMPLE_IMAGE_2]
        )

        for image_name in [self.EXAMPLE_IMAGE_1, self.EXAMPLE_IMAGE_2]:
            metadata = sa.get_item_metadata(self.PROJECT_NAME, image_name)
            self.assertEqual(metadata["annotation_status"], "QualityCheck")

    def test_image_annotation_status_via_invalid_names(self):
        sa.attach_items(
            self.PROJECT_NAME, self.ATTACHMENT_LIST, "InProgress"
        )
        with self.assertRaisesRegexp(AppException, SetAnnotationStatues.ERROR_MESSAGE):
            sa.set_annotation_statuses(
                self.PROJECT_NAME, "QualityCheck", ["self.EXAMPLE_IMAGE_1", "self.EXAMPLE_IMAGE_2"]
            )

    def test_set_annotation_statuses(self):
        sa.attach_items(
            self.PROJECT_NAME, [self.ATTACHMENT_LIST[0]]
        )
        data = sa.set_annotation_statuses(
            self.PROJECT_NAME, annotation_status="Completed", items=[self.ATTACHMENT_LIST[0]["name"]]
        )
        data = sa.search_items(self.PROJECT_NAME)[0]
        assert data["annotation_status"] == "Completed"