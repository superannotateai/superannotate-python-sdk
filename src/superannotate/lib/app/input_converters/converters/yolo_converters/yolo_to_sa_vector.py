"""
YOLO to SA conversion method
"""
import logging
import threading
from glob import glob
from pathlib import Path

import cv2

from ....common import tqdm_converter
from ....common import write_to_json
from ..sa_json_helper import _create_sa_json
from ..sa_json_helper import _create_vector_instance

logger = logging.getLogger("sa")


def yolo_object_detection_to_sa_vector(data_path, output_dir):
    classes = {}
    id_ = 0
    classes_file = open(data_path / "classes.txt")
    for line in classes_file:
        key = line.rstrip()
        if key not in classes.keys():
            classes[id_] = key
            id_ += 1

    annotations = [
        annot for annot in data_path.glob("*.txt") if annot.name != "classes.txt"
    ]

    images_converted = []
    images_not_converted = []
    finish_event = threading.Event()
    tqdm_thread = threading.Thread(
        target=tqdm_converter,
        args=(len(annotations), images_converted, images_not_converted, finish_event),
        daemon=True,
    )
    logger.info("Converting to SuperAnnotate JSON format")
    tqdm_thread.start()
    for annotation in annotations:
        file = open(annotation)
        file_name = "%s.*" % annotation.stem
        files_list = glob(str(data_path / file_name))
        if len(files_list) == 1:
            images_not_converted.append(annotation.name)
            logger.warning("'%s' image for annotation doesn't exist", annotation)
            continue
        if len(files_list) > 2:
            images_not_converted.append(annotation.name)
            logger.warning("'%s' multiple file for this annotation", annotation)
            continue

        if Path(files_list[0]).suffix == ".txt":
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
                float(values[2]) * H + float(values[4]) * H / 2,
            )
            sa_obj = _create_vector_instance("bbox", points, {}, [], classes[class_id])
            sa_instances.append(sa_obj.copy())

        images_converted.append(annotation.name)
        file_name = "%s___objects.json" % Path(file_name).name
        sa_metadata = {"name": Path(file_name).name, "width": W, "height": H}
        sa_json = _create_sa_json(sa_instances, sa_metadata)
        write_to_json(output_dir / file_name, sa_json)

    finish_event.set()
    tqdm_thread.join()
    return classes
