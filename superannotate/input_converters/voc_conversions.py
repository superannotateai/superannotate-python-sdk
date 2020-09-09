import sys
import os
import glob
import shutil
import json
import logging
import copy
import numpy as np
from argparse import Namespace

from .converters.converters import Converter

ALLOWED_TASK_TYPES = ["instance_segmentation", "object_detection"]
ALLOWED_PROJECT_TYPES = ["Pixel", "Vector"]

ALLOWED_CONVERSIONS = [
    ("Pixel", "instance_segmentation"), ("Vector", "object_detection")
]


def load_files():
    pass


def voc_to_sa(args):
    try:
        os.makedirs(args.output_dir)
    except Exception as e:
        logging.error(
            "Could not create output folders, check if they already exist"
        )

    method = Namespace(direction="from", dataset_format=args.dataset_format)

    converter = Converter(
        args.project_type, args.task, args.dataset_name, args.input_dir,
        args.output_dir, method
    )

    try:
        converter.convert_to_sa()
    except Exception as e:
        logging.error("Something went wrong while converting")
        sys.exit()