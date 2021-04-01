from pathlib import Path

import pytest
import superannotate as sa
from superannotate.exceptions import SABaseException

from .common import upload_project

PROJECT_NAME_VECTOR = 'ML Functionality Test Vector'
PROJECT_NAME_PIXEL_PREDICTION = 'ML Functionality Test Pixel Prediction'
PROJECT_NAME_PIXEL_SEGMENTATION = 'ML Functionality Test Pixel Segmentation'
PROJECT_DESCRIPTION = 'testing ml functionality through SDK'
PROJECT_PATH_PIXEL = "./tests/sample_project_pixel_for_ml_functionality"
PROJECT_PATH_VECTOR = "./tests/sample_project_vector_for_ml_functionality"

MODEL_NAME = 'Instance segmentation (trained on COCO)'


def test_run_prediction():

    upload_project(
        Path(PROJECT_PATH_VECTOR), PROJECT_NAME_VECTOR,
        "Test for ml functionality", "Vector"
    )

    upload_project(
        Path(PROJECT_PATH_PIXEL), PROJECT_NAME_PIXEL_PREDICTION,
        "Test for ml functionality", "Pixel"
    )

    #Tests for the case when provided images do not exist in the project
    with pytest.raises(SABaseException) as e:
        sa.run_prediction(
            PROJECT_NAME_VECTOR, ["NonExistantImage.jpg"], MODEL_NAME
        )
        assert str(e) == "No valid image names were provided"

    #Tests that the argument 'project' is valid
    with pytest.raises(SABaseException) as e:
        sa.run_prediction(
            [PROJECT_NAME_VECTOR, PROJECT_NAME_PIXEL_PREDICTION],
            ["DoesntMatter.jpg"], MODEL_NAME
        )
        assert str(
            e
        ) == "smart prediction cannot be run on images from different projects simultaneously"

    #Tests if prediction on all available images gets run
    image_names_pixel = sa.search_images(PROJECT_NAME_PIXEL_PREDICTION)
    image_names_vector = sa.search_images(PROJECT_NAME_VECTOR)

    succeded_imgs, failed_imgs = sa.run_prediction(
        PROJECT_NAME_VECTOR, image_names_vector[:4], MODEL_NAME
    )
    assert (len(succeded_imgs) + len(failed_imgs)) == 4

    succeded_imgs, failed_imgs = sa.run_prediction(
        PROJECT_NAME_PIXEL_PREDICTION, image_names_pixel[:4], MODEL_NAME
    )
    assert (len(succeded_imgs) + len(failed_imgs)) == 4

    succeded_imgs, failed_imgs = sa.run_prediction(
        PROJECT_NAME_PIXEL_PREDICTION, image_names_pixel[:4] + ["NA.jpg"],
        MODEL_NAME
    )
    assert (len(succeded_imgs) + len(failed_imgs)) == 4

    succeded_imgs, failed_imgs = sa.run_prediction(
        PROJECT_NAME_VECTOR, image_names_vector[:4] + ["NA.jpg"], MODEL_NAME
    )
    assert (len(succeded_imgs) + len(failed_imgs)) == 4


def test_run_segmentation():

    model_auto = 'autonomous'
    model_generic = 'generic'

    upload_project(
        Path(PROJECT_PATH_PIXEL), PROJECT_NAME_PIXEL_SEGMENTATION,
        "Test for ml functionality", "Pixel"
    )

    image_names_pixel = sa.search_images(PROJECT_NAME_PIXEL_SEGMENTATION)
    with pytest.raises(SABaseException) as e:
        sa.run_segmentation(PROJECT_NAME_VECTOR, image_names_pixel, model_auto)
        assert str(e) == "Operation not supported for given project type"
    with pytest.raises(SABaseException) as e:
        sa.run_segmentation(
            PROJECT_NAME_PIXEL_SEGMENTATION, image_names_pixel[:2],
            "NonExistantModel"
        )
        assert str(e) == "Model Does not exist"

    with pytest.raises(SABaseException) as e:
        sa.run_segmentation(
            PROJECT_NAME_PIXEL_SEGMENTATION, ["NonExistantImage.jpg"],
            MODEL_NAME
        )
        assert str(e) == "No valid image names were provided"

    succeded_imgs, failed_imgs = sa.run_segmentation(
        PROJECT_NAME_PIXEL_SEGMENTATION, image_names_pixel[:4] + ["NA.jpg"],
        model_generic
    )
    assert (len(succeded_imgs) + len(failed_imgs)) == 4

    succeded_imgs, failed_imgs = sa.run_segmentation(
        PROJECT_NAME_PIXEL_SEGMENTATION, image_names_pixel[:4] + ["NA.jpg"],
        model_auto
    )

    assert (len(succeded_imgs) + len(failed_imgs)) == 4


def test_download_model(tmpdir):
    tmpdir = Path(tmpdir)
    export_dir = Path(tmpdir / 'export')
    export_dir.mkdir(parents=True, exist_ok=True)

    ml_model = sa.search_models(include_global=True)[0]
    model = sa.download_model(ml_model, tmpdir / 'export')
    assert model['name']
    model = sa.download_model(ml_model['name'], tmpdir / 'export')
    assert model['name']
