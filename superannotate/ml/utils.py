from ..db.images import get_image_metadata
from ..common import PredictionSegmentationStatuses
from .defaults import DROP_KEYS
from ast import literal_eval
import pandas as pd
import time
import os

def reformat_metrics_json(data, name):
    continuous_metrics = []
    per_evaluation_metrics = []
    for item in data:
        for key in item:
            try:
                item[key] = literal_eval(item[key])
            except Exception as e:
                pass
        if 'data_time' in item and item['eta_seconds'] != 0:
            continuous_metrics += [item]
        else:
            per_evaluation_metrics += [item]
    continuous_metrics_df = pd.DataFrame.from_dict(continuous_metrics)
    per_evaluation_metrics_df = pd.DataFrame.from_dict(per_evaluation_metrics)
    continuous_metrics_df = drop_non_plotable_cols(
        continuous_metrics_df, DROP_KEYS
    )
    per_evaluation_metrics_df = drop_non_plotable_cols(
        per_evaluation_metrics_df, DROP_KEYS
    )
    continuous_metrics_df['model'] = name
    per_evaluation_metrics_df['model'] = name
    return continuous_metrics_df, per_evaluation_metrics_df


def drop_non_plotable_cols(df, non_plotable_cols):
    for column in df:
        if column not in non_plotable_cols:
            continue
        df = df.drop(columns=column)
    return df


def make_plotly_specs(num_rows):
    specs = [[{"secondary_y": True}] for x in range(num_rows)]
    return specs

def get_images_prediction_segmentation_status(project, image_names, task):
    metadata = get_image_metadata(project,image_names)

    success_names = [x['name'] for x in metadata if x[task] == PredictionSegmentationStatuses.Completed]
    failure_names = [x['name'] for x in metadata if x[task] == PredictionSegmentationStatuses.Failed]
    return success_names, failure_names

def log_process(project, image_name_set, total_image_count,status_key, task, logger):
    num_complete = 0
    succeded_imgs = []
    failed_imgs = []
    while image_name_set:
        succeded_imgs_batch, failed_imgs_batch = set(get_images_prediction_segmentation_status(project, list(image_name_set), status_key))
        complete_images = succeded_imgs_batch + failed_imgs_batch
        succeded_imgs += succeded_imgs_batch
        failed_imgs += failed_imgs_batch
        num_complete += len(complete_images)
        logger.info(f"{task} complete on {num_complete} / {total_image_count} images")
        image_name_set = image_name_set.symmetric_difference(set(complete_images))
        time.sleep(5)
    return (succeded_imgs, failed_imgs)
