import os
from unittest.mock import patch
from os.path import dirname

from src.superannotate import SAClient
sa = SAClient()
from src.superannotate import AppException
from src.superannotate.lib.core import UPLOAD_FOLDER_LIMIT_ERROR_MESSAGE
from src.superannotate.lib.core import UPLOAD_PROJECT_LIMIT_ERROR_MESSAGE
from src.superannotate.lib.core import UPLOAD_USER_LIMIT_ERROR_MESSAGE
from src.superannotate.lib.core import COPY_FOLDER_LIMIT_ERROR_MESSAGE
from src.superannotate.lib.core import COPY_PROJECT_LIMIT_ERROR_MESSAGE
from src.superannotate.lib.core import COPY_SUPER_LIMIT_ERROR_MESSAGE
from tests.integration.base import BaseTestCase
from tests.moks.limitatoins import folder_limit_response
from tests.moks.limitatoins import project_limit_response
from tests.moks.limitatoins import user_limit_response


class TestLimitsUploadImagesFromFolderToProject(BaseTestCase):
    PROJECT_NAME = "TestLimitsUploadImagesFromFolderToProject"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PTH = "data_set"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    EXAMPLE_IMAGE_1 = "example_image_1.jpg"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    @patch("lib.infrastructure.services.SuperannotateBackendService.get_limitations", return_value=folder_limit_response)
    def test_folder_limitations(self, *_):
        with self.assertRaisesRegexp(AppException, UPLOAD_FOLDER_LIMIT_ERROR_MESSAGE):
            _, _, __ = sa.upload_images_from_folder_to_project(
                project=self._project["name"], folder_path=self.folder_path
            )

    @patch("lib.infrastructure.services.SuperannotateBackendService.get_limitations", return_value=project_limit_response)
    def test_project_limitations(self, *_):
        with self.assertRaisesRegexp(AppException, UPLOAD_PROJECT_LIMIT_ERROR_MESSAGE):
            _, _, __ = sa.upload_images_from_folder_to_project(
                project=self._project["name"], folder_path=self.folder_path
            )

    @patch("lib.infrastructure.services.SuperannotateBackendService.get_limitations", return_value=user_limit_response)
    def test_user_limitations(self, *_):
        with self.assertRaisesRegexp(AppException, UPLOAD_USER_LIMIT_ERROR_MESSAGE):
            _, _, __ = sa.upload_images_from_folder_to_project(
                project=self._project["name"], folder_path=self.folder_path
            )


class TestLimitsCopyImage(BaseTestCase):
    PROJECT_NAME = "TestLimitsCopyImage"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    TEST_FOLDER_PTH = "data_set"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    EXAMPLE_IMAGE_1 = "example_image_1.jpg"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    def test_folder_limitations(self):
        sa.upload_image_to_project(self._project["name"], os.path.join(self.folder_path, self.EXAMPLE_IMAGE_1))
        sa.create_folder(self._project["name"], self._project["name"])
        with patch("lib.infrastructure.services.SuperannotateBackendService.get_limitations") as limit_response:
            limit_response.return_value = folder_limit_response
            with self.assertRaisesRegexp(AppException, COPY_FOLDER_LIMIT_ERROR_MESSAGE):
                _, _, __ = sa.copy_image(
                    self._project["name"], self.folder_path, f"{self.PROJECT_NAME}/{self.PROJECT_NAME}")

    def test_project_limitations(self, ):
        sa.upload_image_to_project(self._project["name"], os.path.join(self.folder_path, self.EXAMPLE_IMAGE_1))
        sa.create_folder(self._project["name"], self._project["name"])
        with patch("lib.infrastructure.services.SuperannotateBackendService.get_limitations") as limit_response:
            limit_response.return_value = project_limit_response
            with self.assertRaisesRegexp(AppException, COPY_PROJECT_LIMIT_ERROR_MESSAGE):
                _, _, __ = sa.copy_image(
                    self._project["name"], self.folder_path, f"{self.PROJECT_NAME}/{self.PROJECT_NAME}")

    def test_user_limitations(self, ):
        sa.upload_image_to_project(self._project["name"], os.path.join(self.folder_path, self.EXAMPLE_IMAGE_1))
        sa.create_folder(self._project["name"], self._project["name"])
        with patch("lib.infrastructure.services.SuperannotateBackendService.get_limitations") as limit_response:
            limit_response.return_value = user_limit_response
            with self.assertRaisesRegexp(AppException, COPY_SUPER_LIMIT_ERROR_MESSAGE):
                _, _, __ = sa.copy_image(
                    self._project["name"], self.folder_path, f"{self.PROJECT_NAME}/{self.PROJECT_NAME}")
