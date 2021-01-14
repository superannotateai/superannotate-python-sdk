"""This document containes functions to run smart segmentation, model traing and smart prediction
develoer  : Vahagn Tumanyan
maintainer: Vahagn Tumanyan
email     : Vahagn@superannotate.com
"""
from ..parameter_decorators import project_metadata, model_metadata
from ..common import (
    _AVAILABLE_SEGMENTATION_MODELS, process_api_response,
    project_type_str_to_int, model_training_status_int_to_str
)
from .utils import reformat_metrics_json, make_plotly_specs, log_process
from .defaults import DEFAULT_HYPERPARAMETERS
from ..db.images import get_image_metadata
from plotly.subplots import make_subplots
from ..exceptions import SABaseException
from .defaults import NON_PLOTABLE_KEYS
from ..db.images import search_images
import plotly.graph_objects as go
import plotly.express as px
from ..api import API
import pandas as pd
import logging
import boto3
import json
import time
import os

logger = logging.getLogger("superannotate-python-sdk")
_api = API.get_instance()


def get_valid_image_id(image_name, images_name_id_map):
    if image_name not in images_name_id_map:
        logger.info(
            f"image with the name {image_name} does not exist in the provided project, skipping"
        )
        return None,
    else:
        return (images_name_id_map[image_name], image_name)


def get_valid_image_id_list(project, images_list):
    #TODO use metadata search by name
    images_metadata = search_images(project, return_metadata=True)
    images_name_id_map = {x['name']: x['id'] for x in images_metadata}
    images_id_list = [
        get_valid_image_id(x, images_name_id_map) for x in images_list
    ]
    images_id_list = [x for x in images_id_list if x[0] is not None]
    return images_id_list


@project_metadata
@model_metadata
def run_prediction(project, images_list, model):
    """This function runs smart prediction on given list of images from a given project using the neural network of your choice
    :param project: the project in which the target images are uploaded.
    :type project: str or dict
    :param images_list: the list of image names on which smart prediction has to be run
    :type images_list: list of str
    :param model: the name of the model that should be used for running smart prediction
    :type model: str or dict
    :return status: Returns true if smart prediction successfully started on provided image list
    """

    if not isinstance(project, dict):
        raise SABaseException(
            0,
            "smart prediction cannot be run on images from different projects simultaneously"
        )
    project_id = project["id"]

    images_metadata = get_image_metadata(project, image_names).sort(key = lambda x: x["name"])

    if len(images_metadata) == 0:
        raise SABaseException(0, "No valid image names were provided")

    skipped_images_num = len(images_list) - len(images_metadata)

    if skipped_images_num > 0:
        logger.warning(f"{skipped_images_num} images did not exist in the provided project and were skipped.")

    image_name_set = set([x['name'] for x in images_metadata])
    image_id_list = [x['id'] for x in images_metadata]

    params = {
        "team_id": _api.team_id,
        "project_id": project_id,
        "image_ids": images_id_list,
        "ml_model_id": model["id"]
    }

    response = _api.send_request(
        req_type="POST", json_req=params, path="/images/prediction"
    )

    if not response.ok:
        raise SABaseException(0, "Could not start prediction")

    logger.info("Started smart prediction")
    total_image_count = len(image_name_set)
    succeded_imgs, failed_imgs = log_process(project, image_name_set, total_image_count, 'prediction_status', "Smart Prediction", logger)
    return succeded_imgs, failed_imgs

@project_metadata
def run_segmentation(project, images_list, model):
    """Starts smart segmentation on a list of images using the specified model

    :param project: project name of metadata of the project
    :type  project: str or dict
    :param model  : The model name or metadata of the model
    :type  model  : str or dict
    :return status: returns true if smart segmentation succesfully started, false otherwise
    """

    if not isinstance(project, dict):
        raise SABaseException(
            0,
            "smart prediction cannot be run on images from different projects simultaneously"
        )

    if project['type'] != 'Pixel':
        logger.error(
            f"Smart segmentation is supported only for 'Pixel' projects"
        )
        raise SABaseException(
            0, "Operation not supported for given project type"
        )

    if model not in _AVAILABLE_SEGMENTATION_MODELS:
        logger.error(
            f"the model does not exist, please chose from {_AVAILABLE_SEGMENTATION_MODELS}"
        )
        raise SABaseException(0, "Model Does not exist")


    images_metadata = get_image_metadata(project, image_names).sort(key = lambda x: x["name"])

    if len(images_metadata) == 0:
        raise SABaseException(0, "No valid image names were provided")

    skipped_images_num = len(images_list) - len(images_metadata)

    if skipped_images_num > 0:
        logger.warning(f"{skipped_images_num} images did not exist in the provided project and were skipped.")

    image_name_set = set([x['name'] for x in images_metadata])
    image_id_list = [x['id'] for x in images_metadata]

    json_req = {"model_name": model, "image_ids": images_id_list}

    params = {"team_id": _api.team_id, "project_id": project["id"]}

    response = _api.send_request(
        path=f"/images/segmentation",
        req_type="POST",
        params=params,
        json_req=json_req
    )

    if not response.ok:
        logger.error("Could not start segmentation")
        raise SABaseException(0, "Could not start prediction")

    logger.info("Started smart segmentation")

    succeded_imgs, failed_imgs = log_process(project, image_name_set, total_image_count, 'segmentation_status', 'Smart Segmentation', logger)

    return (succeded_imgs, failed_imgs)


@project_metadata
@model_metadata
def run_training(
    project,
    base_model,
    model_name,
    model_description,
    task,
    hyperparameters,
    log=False
):
    """Runs neural network training
    :param project: project or list of projects that contain the training images
    :type  project: str, dict or list of dict
    :param base_model  : base model on which the new network will be trained
    :type  base_model  : str or dict
    :param model_name   : name of the new model
    :type  model_name   : str
    :param model_description: description of the new model
    :type  model_description: str
    :param task   : The model training task
    :type  task   : str
    :param hyperparameters: hyperparameters that should be used in training
    :type  hyperparameters: dict
    #TODO FIX DOCSTRING (log)
    """

    project_ids = None
    project_type = None

    if isinstance(project, dict):
        project_ids = [project["id"]]
        project_type = project["type"]
        project = [project]
    else:
        project_ids = [x["id"] for x in project]
        types = (x["type"] for x in project)
        types = set(types)
        if len(types) != 1:
            logger.error(
                "All projects have to be of the same type. Either vector or pixel"
            )
            raise SABaseException(0, "Invalid project types")
        project_type = types.pop()

    if project_type != base_model["type"]:
        logger.error(
            "The base model has to be of the same type (vector or pixel) as the projects"
        )
        raise SABaseException(0, "Invalid project and model types")
    for item in DEFAULT_HYPERPARAMETERS:
        if item not in hyperparameters:
            hyperparameters[item] = DEFAULT_HYPERPARAMETERS[item]
    complete_image_count = 0
    for proj in project:
        complete_image_count += proj['completedImagesCount']

    hyperparameters["name"] = model_name
    hyperparameters["description"] = model_description
    hyperparameters["task"] = task
    hyperparameters["base_model_id"] = base_model["id"]
    hyperparameters["project_ids"] = project_ids
    hyperparameters["image_count"] = complete_image_count
    hyperparameters["project_type"] = project_type_str_to_int(project_type)
    params = {
        "team_id": _api.team_id,
    }

    response = _api.send_request(
        req_type="POST",
        path="/ml_models",
        json_req=hyperparameters,
        params=params
    )
    if response.ok:
        logger.info("Started model training")
    else:
        logger.error("Could not start training")
        return response.ok # TODO Raise

    if not log:
        return response.ok

    logger.info(
        "We are firing up servers to run model training. Depending on the number of training images and the task it may take up to 15 minutes until you will start seeing metric reports"
    )
    logger.info(
        "Terminating the function will not terminate model training. If you wish to stop the training please use the stop_model_training function"
    )

    is_training_finished = False
    while not is_training_finished:
        new_model_id = response.json()['id']
        metrics_response = _api.send_request(
            req_type='GET',
            path=f'/ml_model/{new_model_id}/getCurrentMetrics',
            params=params
        )

        metrics_data = metrics_response.json()
        if len(metrics_data) == 1:
            logger.info('Starting up servers')
            time.sleep(30)
        if 'continuous_metrics' in metrics_data:
            logger.info(metrics_data['continuous_metrics'])
        if 'per_evaluation_metrics' in metrics_data:
            for item, value in metrics_data['per_evaluation_metrics'].items():
                logger.info(value)
        if 'training_status' in metrics_data:
            status_str = model_training_status_int_to_str(
                metrics_data['training_status']
            )
            if status_str == 'Completed':
                logger.info('Model Training Successfully completed')
                is_training_finished = True
            elif status_str == 'FailedBeforeEvaluation' or status_str == 'FailedAfterEvaluation':
                logger.info('Failed to train model')
                is_training_finished = True
            elif status_str == 'FailedAfterEvaluationWithSavedModel':
                logger.info(
                    'Model training failed, but we have a checkpoint that can be saved'
                )
                logger.info('Do you wish to save checkpoint (Y/N)?')
                answer = None
                while answer not in ['Y', 'N', 'y', 'n']:
                    answer = input()
                    if answer in ['Y', 'y']:
                        params = {'team_id': _api.team_id}
                        json_req = {'training_status' : 6}
                        response = _api.send_request(
                            req_type = 'PUT'
                            path = f'ml_model/{new_model_id}',
                            params = params,
                            json_req = json_req
                        )
                        logger.info("Model was successfully saved")
                        pass
                    else:
                        delete_model(name)
                        logger.info('The model was not saved')
                is_training_finished = True

        time.sleep(5)
        return new_model_id


@model_metadata
def stop_model_training(model):
    '''This function will stop training model provided by either name or metadata, and return the ID
    :param model: The name or the metadata of the model the training of which the user needs to terminate
    :type model: str or dict
    :out model['id']: the id of the now, stopped model
    '''
    params = {"team_id": _api.team_id}
    response = _api.send_request(
        req_type="POST",
        path=f"/ml_model/{model['id']}/stopTrainingJob",
        params=params
    )

    if response.ok:
        logger.info("Stopped model training")
    else:
        logger.ingo("Failed to stop model training please try again")
    return model['id']

def plot_model_metrics(metric_json_list):
    """plots the metrics generated by neural network using plotly
       :param metric_json_list: list of <model_name>.json files
       :type  metric_json_list: list of str
    """
    def plot_df(df, plottable_cols, figure, start_index = 1):
        for row, metric in enumerate(plottable_cols, start_index):
            for model_df in df:
                name = model_df['model'].iloc[0]
                x_ = model_df.loc[model_df['model'] == name, 'iteration']
                y_ = model_df.loc[model_df['model'] == name, metric]
                figure.add_trace(
                    go.Scatter(x=x_, y=y_, name=name + " " + metric),
                    row=row,
                    col=1
                )

        return figure

    def get_plottable_cols(df, already_taken):
        plottable_cols = []
        for sub_df in df:
            col_names = sub_df.columns.values.tolist()
            for col_name in col_names:
                if col_name not in plottable_cols and col_name not in NON_PLOTABLE_KEYS and col_name not in already_taken:
                    plottable_cols.append(col_name)

        return plottable_cols

    if not isinstance(metric_json_list, list):
        metric_json_list = [metric_json_list]

    full_c_metrics = []
    full_pe_metrics = []
    for metric_json in metric_json_list:
        data = None

        with open(metric_json) as fp:
            data = json.load(fp)
        name = metric_json.split('.')[0]
        c_metrics, pe_metrics = reformat_metrics_json(data, name)
        full_c_metrics.append(c_metrics)
        full_pe_metrics.append(pe_metrics)

    num_rows = 0
    plottable_c_cols = get_plottable_cols(full_c_metrics, [])
    plottable_pe_cols = get_plottable_cols(full_pe_metrics, plottable_c_cols)
    num_rows = len(plottable_c_cols) + len(plottable_pe_cols)
    figure_specs = make_plotly_specs(num_rows)
    num_sublots_per_row = len(metric_json_list)
    plottable_cols = plottable_c_cols + plottable_pe_cols
    figure = make_subplots(
        rows=num_rows,
        cols=1,
        specs=figure_specs,
        subplot_titles = plottable_cols,
    )
    figure.update_layout(
        height= 1000 * len(num_rows)
    )
    models = [os.path.basename(x).split('.')[0] for x in metric_json_list]

    plot_df(full_c_metrics, plottable_c_cols, figure )
    plot_df(full_pe_metrics, plottable_pe_cols, figure, len(plottable_c_cols) )
    figure.show()

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
        os.makedirs(output_dir, exist_ok=True)

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
        req_type="GET",
        path=f"/ml_model/getMyModelDownloadToken/{model['id']}",
        params=params
    )
    if response.ok:
        response = process_api_response(response.json())
    else:
        raise SABaseException(0, "Could not get model info ")

    tokens = response["tokens"]
    s3_session = boto3.Session(
        aws_access_key_id=tokens["accessKeyId"],
        aws_secret_access_key=tokens["secretAccessKey"],
        aws_session_token=tokens["sessionToken"]
    )
    s3_resource = s3_session.resource('s3')

    bucket = s3_resource.Bucket(tokens["bucket"])

    bucket.download_file(config_path, os.path.join(output_dir, 'config.yaml'))
    bucket.download_file(weights_path, os.path.join(output_dir, weights_name))
    try:
        bucket.download_file(
            metrics_path, os.path.join(output_dir, metrics_path)
        )
        bucket.download_file(mapper_path, os.path.join(output_dir, mapper_path))

    except Exception as e:
        logger.info(
            "the specified model does not contain a classes_mapper and/or a metrics file"
        )

    logger.info("Downloaded model related files")

@model_metadata
def delete_model(model):
    params = {"team_id": _api.team_id}
    response = _api.send_request(
        req_type="DELETE", path=f'/ml_model/{model["id"]}', params=params
    )
    if response.ok:
        logger.info("Model successfully deleted")
    else:
        logger.info("Failed to delete model, please try again")

