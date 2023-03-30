from unittest import TestCase
from unittest.mock import patch

from src.superannotate import AppException
from src.superannotate.lib.core.service_types import ServiceResponse
from superannotate import SAClient


sa = SAClient()


class TestSetProjectStatus(TestCase):
    PROJECT_NAME = "test_set_project_status"
    PROJECT_DESCRIPTION = "desc"
    PROJECT_TYPE = "Vector"
    PROJECT_STATUSES = ["NotStarted", "InProgress", "Completed", "OnHold"]

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        cls.tearDownClass()
        cls._project = sa.create_project(
            cls.PROJECT_NAME, cls.PROJECT_DESCRIPTION, cls.PROJECT_TYPE
        )
        project = sa.get_project_metadata(cls.PROJECT_NAME)
        assert project["status"] == "NotStarted"

    @classmethod
    def tearDownClass(cls) -> None:
        sa.delete_project(cls.PROJECT_NAME)

    def test_set_project_status(self):
        with self.assertLogs("sa", level="INFO") as cm:
            for index, status in enumerate(self.PROJECT_STATUSES):
                sa.set_project_status(project=self.PROJECT_NAME, status=status)
                project = sa.get_project_metadata(self.PROJECT_NAME)
                assert (
                    f"INFO:sa:Successfully updated {self.PROJECT_NAME} status to {status}"
                    == cm.output[index]
                )
                self.assertEqual(status, project["status"])
            self.assertEqual(len(cm.output), len(self.PROJECT_STATUSES))

    @patch("lib.infrastructure.services.project.ProjectService.update")
    def test_set_project_status_fail(self, update_function):
        update_function.return_value = ServiceResponse(_error="ERROR")
        with self.assertRaisesRegexp(
            AppException,
            f"Failed to change {self.PROJECT_NAME} status.",
        ):
            sa.set_project_status(project=self.PROJECT_NAME, status="Completed")

    def test_set_project_status_via_invalid_status(self):
        with self.assertRaisesRegexp(
            AppException,
            "Available values are 'NotStarted', 'InProgress', 'Completed', 'OnHold'.",
        ):
            sa.set_project_status(project=self.PROJECT_NAME, status="InvalidStatus")

    def test_set_project_status_via_invalid_project(self):
        with self.assertRaisesRegexp(
            AppException,
            "Project not found.",
        ):
            sa.set_project_status(project="Invalid name", status="Completed")
