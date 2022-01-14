"""
Module which will convert from
superannotate annotation format to other annotation formats
"""
import copy
import json
import shutil
from pathlib import Path

import numpy as np
from superannotate.logger import get_default_logger

from .converters.converters import Converter

logger = get_default_logger()


def _load_files(path_to_imgs, task, ptype):
    suffix = None
    if ptype == "Pixel":
        suffix = "___pixel.json"
    else:
        suffix = "___objects.json"

    orig_images = path_to_imgs.glob("*" + suffix)
    orig_images = [str(x).replace(suffix, "") for x in orig_images]
    all_files = None

    if task == "keypoint_detection":
        all_files = np.array([[fname, fname + suffix] for fname in orig_images])
    elif ptype == "Pixel":
        all_files = np.array(
            [[fname, fname + suffix, fname + "___save.png"] for fname in orig_images]
        )
    elif ptype == "Vector":
        all_files = np.array(
            [[fname, fname + suffix, fname + "___fuse.png"] for fname in orig_images]
        )

    return all_files


def _move_files(data_set, src):
    train_path = src / "image_set"
    if data_set is not None:
        for tup in data_set:
            for i in tup:
                if Path(i).exists():
                    shutil.copy(i, train_path / Path(i).name)
    else:
        logger.warning("Images doesn't exist")


def _create_classes_mapper(imgs, classes_json):
    classes = {}
    j_data = json.load(open(classes_json))
    for instance in j_data:
        classes[instance["name"]] = instance["id"]

    with open(imgs / "image_set" / "classes_mapper.json", "w") as fp:
        json.dump(classes, fp)


def export_from_sa(args):
    """
    :param args: All arguments that will be used during convertion.
    :type args: Namespace
    """
    data_set = None

    (args.output_dir / "image_set").mkdir(parents=True, exist_ok=True)

    try:
        _create_classes_mapper(
            args.output_dir, args.input_dir / "classes" / "classes.json"
        )
    except Exception as e:
        logger.debug(str(e), exc_info=True)
        _create_classes_mapper(args.input_dir, args.output_dir)

    data_set = _load_files(args.input_dir, args.task, args.project_type)
    _move_files(data_set, args.output_dir)

    args.__dict__.update(
        {"direction": "to", "export_root": args.output_dir / "image_set"}
    )
    converter = Converter(args)

    if data_set is not None:
        converter.strategy.set_dataset_name(args.dataset_name)
        converter.convert_from_sa()

    image_set_failed = copy.deepcopy(converter.strategy.failed_conversion_cnt)

    logger.info("Conversion completed")
    return image_set_failed
