import os
import tempfile
from os.path import dirname

import pytest
import src.superannotate as sa
from tests.integration.base import BaseTestCase


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
        with pytest.raises(Exception) as e:
            sa.run_prediction(
                self.PROJECT_NAME, ["NonExistantImage.jpg"], self.MODEL_NAME
            )

    @pytest.mark.flaky(reruns=2)
    def test_run_prediction_for_all_images(self):
        sa.upload_images_from_folder_to_project(
            project=self.PROJECT_NAME, folder_path=self.folder_path
        )
        image_names_vector = sa.search_images(self.PROJECT_NAME)
        succeeded_images, failed_images = sa.run_prediction(
            self.PROJECT_NAME, image_names_vector, self.MODEL_NAME
        )
        assert (len(succeeded_images) + len(failed_images)) == len(image_names_vector)

    def test_download_model(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            ml_model = sa.search_models(include_global=True)[0]
            model = sa.download_model(ml_model, tmp_dir)
            self.assertIsNotNone(model["name"])


class TestSegmentation(BaseTestCase):
    PROJECT_NAME = "TestSegmentation"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Pixel"
    TEST_FOLDER_PTH = "data_set"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    SEGMENTATION_MODEL_AUTONOMOUS = "autonomous"
    SEGMENTATION_MODEL_GENERIC = "generic"

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    def test_run_segmentation(self):
        sa.upload_images_from_folder_to_project(
            project=self.PROJECT_NAME, folder_path=self.folder_path
        )
        image_names_pixel = sa.search_images(self.PROJECT_NAME)
        succeeded_images, failed_images = sa.run_segmentation(
            self.PROJECT_NAME, image_names_pixel, self.SEGMENTATION_MODEL_AUTONOMOUS
        )
        self.assertEqual((len(succeeded_images) + len(failed_images)), 4)


# def test_download_model(tmpdir):
#     tmpdir = Path(tmpdir)
#     export_dir = Path(tmpdir / 'export')
#     export_dir.mkdir(parents=True, exist_ok=True)
#
#     ml_model = sa.search_models(include_global=True)[0]
#     model = sa.download_model(ml_model, tmpdir / 'export')
#     assert model['name']
#     model = sa.download_model(ml_model['name'], tmpdir / 'export')
#     assert model['name']
