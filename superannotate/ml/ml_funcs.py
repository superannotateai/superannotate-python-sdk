"""This document containes functions to run smart segmentation, model traing and smart prediction
develoer  : Vahagn Tumanyan
maintainer: Vahagn Tumanyan
email     : Vahagn@superannotate.com
"""
import plotly.graph_objects as go
import logging
import json
from ..api import API
from .defaults import DEFAULT_HYPERPARAMETERS
from ..exceptions import SABaseException
from .ml_models import _get_model_id_if_exists
from ..common import _AVAILABLE_SEGMENTATION_MODELS
from ..parameter_decorators import project_metadata, model_metadata
from ..db.images import search_images
import boto3
from .utils import reformat_metrics_json, make_plotly_specs
import os
import plotly.express as px
from .defaults import NON_PLOTABLE_KEYS
import pandas as pd
from plotly.subplots import make_subplots
import dash
import dash_core_components as dcc
import dash_html_components as html
import os


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

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
    """Starts smart segmentation on a list of images using the specified model

    :param project: project name of metadata of the project
    :type  project: str or dict
    :param model  : The model name or metadata of the model
    :type  model  : str or dict

    """

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
@model_metadata
def run_training(project, model, name, description, task, hyperparameters):
    """Runs neural network training
    :param project: project or list of projects that contain the training images
    :type  prohect: str, dict or list of dict
    :param model  : base model on which the new network will be trained
    :type  model  : str or dict
    :param name   : name of the new model
    :type  name   : str
    :param description: description of the new model
    :type  description: str
    :param task   : The model training task
    :type  task   : str
    :param hyperparameters: hyperparameters that should be used in training
    :type  hyperparameters: dict
    """

    project_ids = None
    project_type = None

    if isinstance(project, dict):
        project_ids = [project["id"]]
        project_type = project["type"]
    else:
        project_ids = [x["id"] for x in project]
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
    """Downloads the neural network and related files
    which are the <model_name>.pth/pkl. <model_name>.json, <model_name>.yaml, classes_mapper.json
    :param model: the model that needs to be downloaded
    :type  model: str
    :param output_dir: the directiory in which the files will be saved
    :type output_dir: str
    """
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir, exist_ok = True)

    weights_path = model["path"]
    weights_name = os.path.basename(weights_path)
    metrics_name = weights_name.split('.')[0] + '.json'

    config_path = model["config_path"]
    _path = config_path.split("/")
    _path[-1] = "classes_mapper.json"
    mapper_path = "/".join(_path)
    _path[-1] = metrics_name
    metrics_path = "/".join(_path)

    params = {
        "team_id": _api.team_id,
    }

    response = _api.send_request(
        req_type = "GET",
        path = f"/ml_model/getMyModelDownloadToken/{model['id']}",
        params = params
    )
    if response.ok:
        response = response.json()
    else:
        raise SABaseException(
            0, "Could not get model info "
        )

    tokens = response["tokens"]
    s3_session = boto3.Session(
        aws_access_key_id = tokens["accessKeyId"],
        aws_secret_access_key = tokens["secretAccessKey"],
        aws_session_token = tokens["sessionToken"]
    )
    s3_resource = s3_session.resource('s3')

    bucket = s3_resource.Bucket(tokens["bucket"] )

    bucket.download_file(config_path, os.path.join(output_dir, 'config.yaml'))
    bucket.download_file(weights_path, os.path.join(output_dir , weights_name))
    try:
        bucket.download_file(metrics_path, os.path.join(output_dir, metrics_path))
        bucket.download_file(mapper_path, os.path.join(output_dir, mapper_path))
    except Exception as e:
        logger.info("the specified model does not contain a classes_mapper and/or a metrics file")

    logger.info("Downloaded model related files")


def plot_model_metrics(metric_json_list):
    """plots the metrics generated by neural network using plotly
       :param metric_json_list: list of <model_name>.json files
       :type  metric_json_list: list of str
    """
    if not isinstance(metric_json_list, list):
        metric_json_list = [metric_json_list]

    full_c_metrics = []
    full_pe_metrics = []
    for metric_json in metric_json_list:
        data = None

        with open(metric_json) as fp:
            data = json.load(fp)
        name = metric_json.split('.')[0]
        c_metrics, pe_metrics = reformat_metrics_json(data, name )
        full_c_metrics.append(c_metrics)
        full_pe_metrics.append(pe_metrics)

    num_rows = 0
    plottable_cols = []
    for df in full_c_metrics:
        col_names = df.columns.values.tolist()
        for col_name in col_names:
            if col_name not in plottable_cols and col_name not in NON_PLOTABLE_KEYS:
                plottable_cols.append(col_name)
    num_rows = len(metric_json_list)
    figure_specs = make_plotly_specs(num_rows)
    num_sublots_per_row = len(metric_json_list)
    figure = make_subplots(rows = num_rows, cols = 1, specs = figure_specs, subplot_titles = plottable_cols)
    figure.print_grid()
    models = [os.path.basename(x).split('.')[0] for x in metric_json_list]
    for row, metric in enumerate(plottable_cols, 1):
        for model_df in full_c_metrics:
            name = model_df['model'].iloc[0]
            x_ = model_df.loc[model_df['model'] == name, 'iteration']
            y_ = model_df.loc[model_df['model'] == name, metric]
            figure.add_trace(go.Scatter(x = x_, y = y_, name = name + " " + metric), row = row, col = 1)
    figure.show()



