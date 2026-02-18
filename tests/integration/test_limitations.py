import os
from os.path import dirname
from unittest.mock import patch

from src.superannotate import AppException
from src.superannotate import SAClient
from src.superannotate.lib.core import UPLOAD_FOLDER_LIMIT_ERROR_MESSAGE
from src.superannotate.lib.core import UPLOAD_PROJECT_LIMIT_ERROR_MESSAGE
from src.superannotate.lib.core import UPLOAD_USER_LIMIT_ERROR_MESSAGE
from tests.integration.base import BaseTestCase
from tests.moks.limitatoins import folder_limit_response
from tests.moks.limitatoins import project_limit_response
from tests.moks.limitatoins import user_limit_response

sa = SAClient()


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

    @patch(
        "lib.infrastructure.serviceprovider.ServiceProvider.get_limitations",
        return_value=folder_limit_response,
    )
    def test_folder_limitations(self, *_):
        with self.assertRaisesRegexp(AppException, UPLOAD_FOLDER_LIMIT_ERROR_MESSAGE):
            _, _, __ = sa.upload_images_from_folder_to_project(
                project=self._project["name"], folder_path=self.folder_path
            )

    @patch(
        "lib.infrastructure.serviceprovider.ServiceProvider.get_limitations",
        return_value=project_limit_response,
    )
    def test_project_limitations(self, *_):
        with self.assertRaisesRegexp(AppException, UPLOAD_PROJECT_LIMIT_ERROR_MESSAGE):
            _, _, __ = sa.upload_images_from_folder_to_project(
                project=self._project["name"], folder_path=self.folder_path
            )

    @patch(
        "lib.infrastructure.serviceprovider.ServiceProvider.get_limitations",
        return_value=user_limit_response,
    )
    def test_user_limitations(self, *_):
        with self.assertRaisesRegexp(AppException, UPLOAD_USER_LIMIT_ERROR_MESSAGE):
            _, _, __ = sa.upload_images_from_folder_to_project(
                project=self._project["name"], folder_path=self.folder_path
            )
