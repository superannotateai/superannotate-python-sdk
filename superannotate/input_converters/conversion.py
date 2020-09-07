import sys
import os
from argparse import Namespace

from .coco_conversions import coco_to_sa, sa_to_coco

AVAILABLE_DATASET_FORMAT_CONVERTERS = ["COCO"]


def convert_annotation_format_to(
    input_dir,
    output_dir,
    dataset_format,
    dataset_name,
    project_type,
    task,
    train_val_split_ratio=80,
    copyQ=True
):
    """This is a method to convert superannotate annotation formate to the other annotation formats.
    :param input_dir: Path to the dataset folder that you want to convert.
    :type input_dir: string
    :param output_dir: Path to the folder, where you want to have converted dataset.
    :type output_dir: string
    :param dataset_format: One of the formats that are possible to convert. Choose from ["COCO",]
    :type dataset_format: string
    :param dataset_name: Name of the dataset.
    :type dataset_name: string
    :param project_type: Project type is either 'vector' or 'pixel'
    :type project_type: string
    :param task: Choose one from possible candidates. ['panoptic_segmentation', 'instance_segmentation', 'keypoint_detection', 'object_detection']
    :type task: string
    :param train_val_split_ratio: Percentage of data to split between test and train. (Default: 80)
    :type train_val_split_ratio: float, optional
    :param copyQ: Copy original images or move (Default: True, copies) 
    :type copyQ: boolean, optional
    """

    if dataset_format not in AVAILABLE_DATASET_FORMAT_CONVERTERS:
        raise ValueError(
            "'{}' converter doesn't exist. Possible candidates are '{}'".format(
                dataset_format, AVAILABLE_DATASET_FORMAT_CONVERTERS
            )
        )

    args = Namespace(
        input_dir=input_dir,
        output_dir=output_dir,
        dataset_format=dataset_format,
        dataset_name=dataset_name,
        project_type=project_type,
        task=task,
        train_val_split_ratio=train_val_split_ratio,
        copyQ=copyQ
    )

    if dataset_format == "COCO":
        sa_to_coco(args)
    elif dataset_format == "VOC":
        pass
        # sa_to_voc(args)
    else:
        pass

def convert_annotation_format_from(
    input_dir,
    output_dir,
    dataset_format,
    dataset_name,
    project_type,
    task,
    copyQ=True
):
    """This is a method to convert other annotation formats to superannotate annotation format.
    :param input_dir: Path to the dataset folder that you want to convert.
    :type input_dir: string
    :param output_dir: Path to the folder, where you want to have converted dataset.
    :type output_dir: string
    :param dataset_format: One of the formats that are possible to convert. Choose from ["COCO",]
    :type dataset_format: string
    :param dataset_name: Name of the dataset.
    :type dataset_name: string
    :param project_type: Project type is either 'vector' or 'pixel'
    :type project_type: string
    :param task: Choose one from possible candidates. ['panoptic_segmentation', 'instance_segmentation', 'keypoint_detection', 'object_detection']
    :type task: string
    :param copyQ: Copy original images or move (Default: True, copies) 
    :type copyQ: boolean, optional
    """

    if dataset_format not in AVAILABLE_DATASET_FORMAT_CONVERTERS:
        raise ValueError(
            "'{}' converter doesn't exist. Possible candidates are '{}'".format(
                dataset_format, AVAILABLE_DATASET_FORMAT_CONVERTERS
            )
        )

    args = Namespace(
        input_dir=input_dir,
        output_dir=output_dir,
        dataset_format=dataset_format,
        dataset_name=dataset_name,
        project_type=project_type,
        task=task,
        copyQ=copyQ
    )

    if dataset_format == "COCO":
        coco_to_sa(args)
    elif dataset_format == "VOC":
        pass
        # voc_to_sa(args)
    else:
        pass
