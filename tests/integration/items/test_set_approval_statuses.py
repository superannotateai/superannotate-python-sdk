import os
from pathlib import Path

from src.superannotate import AppException
from src.superannotate import SAClient
from tests.integration.base import BaseTestCase

sa = SAClient()


ATTACHMENT_LIST = [
        {
            "url": "https://drive.google.com/uc?export=download&id=1vwfCpTzcjxoEA4hhDxqapPOVvLVeS7ZS",
            "name": "6022a74d5384c50017c366b3",
        },
        {
            "url": "https://drive.google.com/uc?export=download&id=1geS2YtQiTYuiduEirKVYxBujHJaIWA3V",
            "name": "6022a74b5384c50017c366ad",
        },
        {"url": "1SfGcn9hdkVM35ZP0S93eStsE7Ti4GtHU", "name": "123"},
        {
            "url": "https://drive.google.com/uc?export=download&id=1geS2YtQiTYuiduEirKVYxBujHJaIWA3V",
            "name": "6022a74b5384c50017c366ad",
        },
    ]


class TestSetApprovalStatuses(BaseTestCase):
    PROJECT_NAME = "TestSetApprovalStatuses"
    PROJECT_DESCRIPTION = "TestSetApprovalStatuses"
    PROJECT_TYPE = "Vector"
    FOLDER_NAME = "test_folder"
    CSV_PATH = "data_set/attach_urls.csv"
    EXAMPLE_IMAGE_1 = "6022a74d5384c50017c366b3"
    EXAMPLE_IMAGE_2 = "6022a74b5384c50017c366ad"

    @property
    def scv_path(self):
        return os.path.join(Path(__file__).parent.parent.parent, self.CSV_PATH)

    def test_image_approval_status(self):
        sa.attach_items(self.PROJECT_NAME, ATTACHMENT_LIST)

        sa.set_approval_statuses(
            self.PROJECT_NAME,
            "Approved",
        )
        for image in sa.search_items(self.PROJECT_NAME):
            self.assertEqual(image["approval_status"], "Approved")

    def test_image_approval_status_via_names(self):
        sa.attach_items(self.PROJECT_NAME, ATTACHMENT_LIST)

        sa.set_approval_statuses(
            self.PROJECT_NAME, "Approved", [self.EXAMPLE_IMAGE_1, self.EXAMPLE_IMAGE_2]
        )

        for image_name in [self.EXAMPLE_IMAGE_1, self.EXAMPLE_IMAGE_2]:
            metadata = sa.get_item_metadata(self.PROJECT_NAME, image_name)
            self.assertEqual(metadata["approval_status"], "Approved")

    def test_image_approval_status_via_invalid_names(self):
        sa.attach_items(self.PROJECT_NAME, ATTACHMENT_LIST, "InProgress")
        with self.assertRaisesRegexp(AppException, "No items found."):
            sa.set_approval_statuses(
                self.PROJECT_NAME,
                "Approved",
                ["self.EXAMPLE_IMAGE_1", "self.EXAMPLE_IMAGE_2"],
            )

    def test_set_approval_statuses(self):
        sa.attach_items(self.PROJECT_NAME, [ATTACHMENT_LIST[0]])
        sa.set_approval_statuses(
            self.PROJECT_NAME,
            approval_status=None,
            items=[ATTACHMENT_LIST[0]["name"]],
        )
        data = sa.search_items(self.PROJECT_NAME)[0]
        assert data["approval_status"] is None

    def test_set_invalid_approval_statuses(self):
        sa.attach_items(self.PROJECT_NAME, [ATTACHMENT_LIST[0]])
        with self.assertRaisesRegexp(
            AppException, "Available values are 'Approved', 'Disapproved'."
        ):
            sa.set_approval_statuses(
                self.PROJECT_NAME,
                approval_status="aaa",  # noqa
                items=[ATTACHMENT_LIST[0]["name"]],
            )


class TestDocumentSetApprovalStatuses(BaseTestCase):
    PROJECT_NAME = "TestDocumentSetApprovalStatuses"
    PROJECT_DESCRIPTION = "TestDocumentSetApprovalStatuses"
    PROJECT_TYPE = "Document"

    def test_item_approval_status(self):
        sa.attach_items(self.PROJECT_NAME, ATTACHMENT_LIST)

        sa.set_approval_statuses(
            self.PROJECT_NAME,
            "Approved",
        )
        for item in sa.search_items(self.PROJECT_NAME):
            self.assertEqual(item["approval_status"], "Approved")
