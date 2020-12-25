import logging
import os
from glob import glob

import cv2
import numpy as np

from ..sa_json_helper import _create_vector_instance

logger = logging.getLogger("superannotate-python-sdk")


def _create_classes(classes):
    classes_loader = []
    for id_, name in classes.items():
        color = np.random.choice(range(256), size=3)
        hexcolor = "#%02x%02x%02x" % tuple(color)
        sa_classes = {'name': name, 'color': hexcolor, 'attribute_groups': []}
        classes_loader.append(sa_classes)
    return classes_loader


def yolo_object_detection_to_sa_vector(data_path):
    classes = {}
    id_ = 0
    classes_file = open(data_path / 'classes.txt')
    for line in classes_file:
        key = line.rstrip()
        if key not in classes.keys():
            classes[id_] = key
            id_ += 1

    annotations = data_path.glob('*.txt')

    sa_jsons = {}
    for annotation in annotations:
        base_name = annotation.name
        if base_name == 'classes.txt':
            continue

        file = open(annotation)
        file_name = os.path.splitext(base_name)[0] + '.*'
        files_list = glob(os.path.join(data_path, file_name))
        if len(files_list) == 1:
            logger.warning(
                "'{}' image for annotation doesn't exist".format(annotation)
            )
            continue
        elif len(files_list) > 2:
            logger.warning(
                "'{}' multiple file for this annotation".format(annotation)
            )
            continue
        else:
            if os.path.splitext(files_list[0])[1] == '.txt':
                file_name = files_list[1]
            else:
                file_name = files_list[0]
        img = cv2.imread(file_name)
        H, W, _ = img.shape

        sa_loader = []
        for line in file:
            values = line.split()
            class_id = int(values[0])
            points = (
                float(values[1]) * W - float(values[3]) * W / 2,
                float(values[2]) * H - float(values[4]) * H / 2,
                float(values[1]) * W + float(values[3]) * W / 2,
                float(values[2]) * H + float(values[4]) * H / 2
            )
            sa_obj = _create_vector_instance(
                'bbox', points, {}, [], classes[class_id]
            )
            sa_loader.append(sa_obj.copy())

        file_name = '%s___objects.json' % os.path.basename(file_name)
        sa_jsons[file_name] = sa_loader

    return sa_jsons, _create_classes(classes)
