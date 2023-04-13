import os
from os.path import dirname

import pytest
from src.superannotate import AppException
from src.superannotate import SAClient
from tests.integration.base import BaseTestCase

sa = SAClient()


class TestMlFuncs(BaseTestCase):
    PROJECT_NAME = "rename preoject"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    NEW_PROJECT_NAME = "new"
    TEST_FOLDER_PTH = "data_set"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    MODEL_NAME = "Instance segmentation (trained on COCO)"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    def test_run_prediction_with_non_exist_images(self):
        with self.assertRaisesRegexp(
            AppException, "No valid image names were provided."
        ):
            sa.run_prediction(
                self.PROJECT_NAME, ["NotExistingImage.jpg"], self.MODEL_NAME
            )

    @pytest.mark.skip(reason="Test skipped due to long execution")
    def test_run_prediction_for_all_images(self):
        sa.upload_images_from_folder_to_project(
            project=self.PROJECT_NAME, folder_path=self.folder_path
        )
        image_names_vector = [i["name"] for i in sa.search_items(self.PROJECT_NAME)]
        succeeded_images, failed_images = sa.run_prediction(
            self.PROJECT_NAME, image_names_vector, self.MODEL_NAME
        )
        assert (len(succeeded_images) + len(failed_images)) == len(image_names_vector)
