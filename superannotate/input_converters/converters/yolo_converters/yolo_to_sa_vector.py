import logging

from pathlib import Path
from glob import glob

import cv2

from ..sa_json_helper import (_create_vector_instance, _create_sa_json)

from ....common import write_to_json

logger = logging.getLogger("superannotate-python-sdk")


def yolo_object_detection_to_sa_vector(data_path, output_dir):
    classes = {}
    id_ = 0
    classes_file = open(data_path / 'classes.txt')
    for line in classes_file:
        key = line.rstrip()
        if key not in classes.keys():
            classes[id_] = key
            id_ += 1

    annotations = data_path.glob('*.txt')

    for annotation in annotations:
        base_name = annotation.name
        if base_name == 'classes.txt':
            continue

        file = open(annotation)
        file_name = '%s.*' % annotation.stem
        files_list = glob(str(data_path / file_name))
        if len(files_list) == 1:
            logger.warning(
                "'%s' image for annotation doesn't exist" % (annotation)
            )
            continue
        if len(files_list) > 2:
            logger.warning(
                "'%s' multiple file for this annotation" % (annotation)
            )
            continue

        if Path(files_list[0]).suffix == '.txt':
            file_name = files_list[1]
        else:
            file_name = files_list[0]

        img = cv2.imread(file_name)
        H, W, _ = img.shape

        sa_instances = []
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
            sa_instances.append(sa_obj.copy())

        file_name = '%s___objects.json' % Path(file_name).name
        sa_metadata = {'name': Path(file_name).name, 'width': W, 'height': H}
        sa_json = _create_sa_json(sa_instances, sa_metadata)
        write_to_json(output_dir / file_name, sa_json)

    return classes
