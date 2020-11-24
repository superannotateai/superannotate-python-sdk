"""This document containes functions to run smart segmentation, model traing and smart prediction
develoer  : Vahagn Tumanyan
maintainer: Vahagn Tumanyan
email     : Vahagn@superannotate.com
"""

import logging
from ..api import API
from .defaults import DEFAULT_HYPERPARAMETERS
from ..exceptions import SABaseException
from .ml_models import _get_model_id_if_exists
from ..common import _AVAILABLE_SEGMENTATION_MODELS
from .decorators import project_metadata, model_metadata
from ..db.images import search_images
logger = logging.getLogger("superannotate-python-sdk")
_api = API.get_instance()

def _heto_kjogem(image_name, images_name_id_map):
    if image_name not in images_name_id_map:
        logger.info(f"image with the name {image_name} does not exist in the provided project, skipping")
    else:
        return images_name_id_map[image_name]
@project_metadata
@model_metadata
def run_prediction(project, images_list, model):
    """This function runs smart prediction on given list of images from a given project using the neural network of your choice
    :param project: the project in which the target images are uploaded.
    :type project: str or dict
    :param images_list: the list of image names on which smart prediction has to be run
    :type images_list: list of str
    :param model: the name of the model that should be used for running smart prediction
    :type model: str or dict """
    if not isinstance(project, dict):
        raise SABaseException(
            0, "smart prediction cannot be run on images from different projects simultaneously"
        )
    project_id = project["id"]
    images_metadata = search_images(project, return_metadata = True)
    images_name_id_map = {x['name']:x['id'] for x in images_metadata}
    images_id_list = [_heto_kjogem(x, images_name_id_map) for x in images_list]
    images_id_list = [x for x in images_id_list if x is not None]
    if len(images_id_list) == 0:
        raise SABaseException(
            0, "No valid image names were provided"
        )
    params = {
        "team_id": _api.team_id,
        "project_id": project_id,
        "image_ids": images_id_list,
        "ml_model_id": model["id"]
    }
    response = _api.send_request(
        req_type = "POST",
        json_req = params,
        path = f"/images/prediction"
    )

    if not response.ok:
        raise SABaseException(
            0, "Could not start prediction"
        )

    logger.info("Started smart prediction")

@project_metadata
def run_segmentation(project, images_list, model):

    if not isinstance(project, dict):
        raise SABaseException(
            0, "smart prediction cannot be run on images from different projects simultaneously"
        )

    if model not in _AVAILABLE_SEGMENTATION_MODELS:
        logger.error(f"the model does not exist, please chose from {_AVAILABLE_SEGMENTATION_MODELS}")
        raise SABaseException(
            0, "Model Does not exist"
        )

    images_metadata = search_images(project, return_metadata = True)
    images_name_id_map = {x['name']:x['id'] for x in images_metadata}
    images_id_list = [_heto_kjogem(x, images_name_id_map) for x in images_list]
    images_id_list = [x for x in images_id_list if x is not None]

    if len(images_id_list) == 0:
        raise SABaseException(
            0, "No valid image names were provided"
        )

    json_req = {
        "model_name" : model,
        "image_ids": images_id_list
    }

    params = {
        "team_id" : _api.team_id,
        "project_id": project["id"]
    }

    response = _api.send_request(
        path = f"/images/segmentation",
        req_type = "POST",
        params = params,
        json_req = json_req
    )

    if not response.ok:
        logger.error("Could not start segmentation")
    else:
        logger.info("Started smart segmentation")

@project_metadata
def run_training(project, model, name, description, task, hyperparameters):
    project_ids = None
    project_type = None

    if isinstance(project, dict):
        project_ids = [project["id"]]
        project_type = project["type"]
    else:
        project_ids = [x["id"] for in project]
        types = (x["type"] for x in project)

        if len(types) != 1:
            logger.error("All projects have to be of the same type. Either vector or pixel")
            raise SABaseException(
                0, "Invalid project types"
            )
        project_type = types.pop()

    if project_type != model["type"]:
        logger.error("The base model has to be of the same type (vector or pixel) as the projects")
        raise SABaseException(
            0, "Invalid project and model types"
        )

    for item in DEFAULT_HYPERPARAMETERS:
        if item not in hyperparameters:
            hyperparameters[item] = DEFAULT_HYPERPARAMETERS[item]

    hyperparameters["name"] = name
    hyperparameters["description"] = description
    hyperparameters["task"] = task
    hyperparameters["base_ml_model"] = model["id"]
    hyperparameters["project_ids"] = project_ids

    params = {
        "team_id" : _api.team_id,
    }


    response =_api.send_request(
        req_type = "POST",
        path = "/ml_model",
        json_req = hyperparameters
    )

    if response.ok:
        logger.info("Started model training")
    else:
        res = response.json()
        logger.error(res["error"])

@model_metadata
def download_model(model, output_dir):
    pass
