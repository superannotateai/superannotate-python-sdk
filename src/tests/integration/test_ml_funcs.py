import time
import src.lib.app.superannotate as sa
from src.tests.integration.base import BaseTestCase
import os
from os.path import dirname
import pytest
import tempfile
from pathlib import Path



class TestMlFuncs(BaseTestCase):
    PROJECT_NAME = "rename"
    PROJECT_DESCRIPTION = "Desc"
    PROJECT_TYPE = "Vector"
    NEW_PROJECT_NAME = "new"
    TEST_FOLDER_PTH = "data_set"
    TEST_FOLDER_PATH = "data_set/sample_project_vector"
    MODEL_NAME = 'Instance segmentation (trained on COCO)'

    @property
    def folder_path(self):
        return os.path.join(dirname(dirname(__file__)), self.TEST_FOLDER_PATH)

    def test_run_prediction_with_non_exist_images(self):
        with pytest.raises(Exception) as e:
            sa.run_prediction(self.PROJECT_NAME, ["NonExistantImage.jpg"], self.MODEL_NAME)

    def test_run_prediction_for_all_images(self):
        sa.upload_images_from_folder_to_project(
            project=self.PROJECT_NAME,folder_path=self.folder_path
        )
        time.sleep(2)
        image_names_vector = sa.search_images(self.PROJECT_NAME)
        succeeded_images, failed_images = sa.run_prediction(
            self.PROJECT_NAME, image_names_vector, self.MODEL_NAME
        )
        assert (len(succeeded_images) + len(failed_images)) == len(image_names_vector)

    def test_download_model(self):
        tmpdir = tempfile.TemporaryDirectory()
        ml_model = sa.search_models(include_global=True)[0]
        model = sa.download_model(ml_model, tmpdir.name)
        assert model['name']
        model = sa.download_model(ml_model['name'], tmpdir.name)
        assert model['name']



class TestSegmentation(BaseTestCase):
    PROJECT_NAME = "segm"
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
        time.sleep(2)
        image_names_pixel = sa.search_images(self.PROJECT_NAME)
        succeeded_images, failed_images = sa.run_segmentation(
                self.PROJECT_NAME, image_names_pixel,
                self.SEGMENTATION_MODEL_AUTONOMOUS
            )
        assert (len(succeeded_images) + len(failed_images)) == 4




# from pathlib import Path
#
# import pytest
# import superannotate as sa
# from superannotate.exceptions import SABaseException
#
# from .common import upload_project
#
# PROJECT_NAME_VECTOR = 'ML Functionality Test Vector'
# PROJECT_NAME_PIXEL_PREDICTION = 'ML Functionality Test Pixel Prediction'
# PROJECT_NAME_PIXEL_SEGMENTATION = 'ML Functionality Test Pixel Segmentation'
# PROJECT_DESCRIPTION = 'testing ml functionality through SDK'
# PROJECT_PATH_PIXEL = "./tests/sample_project_pixel_for_ml_functionality"
# PROJECT_PATH_VECTOR = "./tests/sample_project_vector_for_ml_functionality"
#
# MODEL_NAME = 'Instance segmentation (trained on COCO)'
#
#
# def test_run_prediction():
#
#     upload_project(
#         Path(PROJECT_PATH_VECTOR), PROJECT_NAME_VECTOR,
#         "Test for ml functionality", "Vector"
#     )
#
#     upload_project(
#         Path(PROJECT_PATH_PIXEL), PROJECT_NAME_PIXEL_PREDICTION,
#         "Test for ml functionality", "Pixel"
#     )
#
#     #Tests for the case when provided images do not exist in the project
#     with pytest.raises(SABaseException) as e:
#         sa.run_prediction(
#             PROJECT_NAME_VECTOR, ["NonExistantImage.jpg"], MODEL_NAME
#         )
#         assert str(e) == "No valid image names were provided"
#
#     #Tests that the argument 'project' is valid
#     with pytest.raises(SABaseException) as e:
#         sa.run_prediction(
#             [PROJECT_NAME_VECTOR, PROJECT_NAME_PIXEL_PREDICTION],
#             ["DoesntMatter.jpg"], MODEL_NAME
#         )
#         assert str(
#             e
#         ) == "smart prediction cannot be run on images from different projects simultaneously"
#
#     #Tests if prediction on all available images gets run
#     image_names_pixel = sa.search_images(PROJECT_NAME_PIXEL_PREDICTION)
#     image_names_vector = sa.search_images(PROJECT_NAME_VECTOR)
#
#     succeded_imgs, failed_imgs = sa.run_prediction(
#         PROJECT_NAME_VECTOR, image_names_vector[:4], MODEL_NAME
#     )
#     assert (len(succeded_imgs) + len(failed_imgs)) == 4
#
#     succeded_imgs, failed_imgs = sa.run_prediction(
#         PROJECT_NAME_PIXEL_PREDICTION, image_names_pixel[:4], MODEL_NAME
#     )
#     assert (len(succeded_imgs) + len(failed_imgs)) == 4
#
#     succeded_imgs, failed_imgs = sa.run_prediction(
#         PROJECT_NAME_PIXEL_PREDICTION, image_names_pixel[:4] + ["NA.jpg"],
#         MODEL_NAME
#     )
#     assert (len(succeded_imgs) + len(failed_imgs)) == 4
#
#     succeded_imgs, failed_imgs = sa.run_prediction(
#         PROJECT_NAME_VECTOR, image_names_vector[:4] + ["NA.jpg"], MODEL_NAME
#     )
#     assert (len(succeded_imgs) + len(failed_imgs)) == 4
#
#
# def test_run_segmentation():
#
#     model_auto = 'autonomous'
#     model_generic = 'generic'
#
#     upload_project(
#         Path(PROJECT_PATH_PIXEL), PROJECT_NAME_PIXEL_SEGMENTATION,
#         "Test for ml functionality", "Pixel"
#     )
#
#     image_names_pixel = sa.search_images(PROJECT_NAME_PIXEL_SEGMENTATION)
#     with pytest.raises(SABaseException) as e:
#         sa.run_segmentation(PROJECT_NAME_VECTOR, image_names_pixel, model_auto)
#         assert str(e) == "Operation not supported for given project type"
#     with pytest.raises(SABaseException) as e:
#         sa.run_segmentation(
#             PROJECT_NAME_PIXEL_SEGMENTATION, image_names_pixel[:2],
#             "NonExistantModel"
#         )
#         assert str(e) == "Model Does not exist"
#
#     with pytest.raises(SABaseException) as e:
#         sa.run_segmentation(
#             PROJECT_NAME_PIXEL_SEGMENTATION, ["NonExistantImage.jpg"],
#             MODEL_NAME
#         )
#         assert str(e) == "No valid image names were provided"
#
#     succeded_imgs, failed_imgs = sa.run_segmentation(
#         PROJECT_NAME_PIXEL_SEGMENTATION, image_names_pixel[:4] + ["NA.jpg"],
#         model_generic
#     )
#     assert (len(succeded_imgs) + len(failed_imgs)) == 4
#
#     succeded_imgs, failed_imgs = sa.run_segmentation(
#         PROJECT_NAME_PIXEL_SEGMENTATION, image_names_pixel[:4] + ["NA.jpg"],
#         model_auto
#     )
#
#     assert (len(succeded_imgs) + len(failed_imgs)) == 4
#
#
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
