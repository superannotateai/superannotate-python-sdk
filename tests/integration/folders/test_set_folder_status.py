from unittest import TestCase
from unittest.mock import patch

from src.superannotate import AppException
from src.superannotate.lib.core.service_types import ServiceResponse
from superannotate import SAClient


sa = SAClient()


class TestSetFolderStatus(TestCase):
    PROJECT_NAME = "test_set_folder_status"
    FOLDER_NAME = "test_folder"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"
    FOLDER_STATUSES = ["NotStarted", "InProgress", "Completed", "OnHold"]

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        cls.tearDownClass()
        cls._project = sa.create_project(
            cls.PROJECT_NAME, cls.PROJECT_DESCRIPTION, cls.PROJECT_TYPE
        )
        sa.create_folder(cls.PROJECT_NAME, cls.FOLDER_NAME)
        folder = sa.get_folder_metadata(
            project=cls.PROJECT_NAME, folder_name=cls.FOLDER_NAME
        )
        assert folder["status"] == "NotStarted"

    @classmethod
    def tearDownClass(cls) -> None:
        sa.delete_project(cls.PROJECT_NAME)

    def test_set_folder_status(self):
        with self.assertLogs("sa", level="INFO") as cm:
            for index, status in enumerate(self.FOLDER_STATUSES):
                sa.set_folder_status(
                    project=self.PROJECT_NAME, folder=self.FOLDER_NAME, status=status
                )
                folder = sa.get_folder_metadata(
                    project=self.PROJECT_NAME, folder_name=self.FOLDER_NAME
                )
                assert (
                    f"INFO:sa:Successfully updated {self.PROJECT_NAME}/{self.FOLDER_NAME} status to {status}"
                    == cm.output[index]
                )
                self.assertEqual(status, folder["status"])
            self.assertEqual(len(cm.output), len(self.FOLDER_STATUSES))

    @patch("lib.infrastructure.services.folder.FolderService.update")
    def test_set_folder_status_fail(self, update_function):
        update_function.return_value = ServiceResponse(_error="ERROR")
        with self.assertRaisesRegexp(
            AppException,
            f"Failed to change {self.PROJECT_NAME}/{self.FOLDER_NAME} status.",
        ):
            sa.set_folder_status(
                project=self.PROJECT_NAME, folder=self.FOLDER_NAME, status="Completed"
            )

    def test_set_folder_status_via_invalid_status(self):
        with self.assertRaisesRegexp(
            AppException,
            "Available values are 'NotStarted', 'InProgress', 'Completed', 'OnHold'.",
        ):
            sa.set_folder_status(
                project=self.PROJECT_NAME,
                folder=self.FOLDER_NAME,
                status="InvalidStatus",
            )

    def test_set_folder_status_via_invalid_project(self):
        with self.assertRaisesRegexp(
            AppException,
            "Project not found.",
        ):
            sa.set_folder_status(
                project="Invalid Name", folder=self.FOLDER_NAME, status="Completed"
            )

    def test_set_folder_status_via_invalid_folder(self):
        with self.assertRaisesRegexp(
            AppException,
            "Folder not found.",
        ):
            sa.set_folder_status(
                project=self.PROJECT_NAME, folder="Invalid Name", status="Completed"
            )
