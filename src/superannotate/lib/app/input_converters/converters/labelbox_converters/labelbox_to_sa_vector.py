"""
Labelbox to SA conversion method
"""
import threading

import cv2
from superannotate.logger import get_default_logger

from ....common import tqdm_converter
from ....common import write_to_json
from ..sa_json_helper import _create_sa_json
from ..sa_json_helper import _create_vector_instance
from .labelbox_helper import _create_attributes_list
from .labelbox_helper import _create_classes_id_map

logger = get_default_logger()


def labelbox_to_sa(json_data, output_dir, task):
    classes = _create_classes_id_map(json_data)
    if task == "object_detection":
        instance_types = ["bbox"]
    elif task == "instance_segmentation":
        instance_types = ["polygon"]
    elif task == "vector_annotation":
        instance_types = ["bbox", "polygon", "line", "point"]

    images_converted = []
    images_not_converted = []
    finish_event = threading.Event()
    tqdm_thread = threading.Thread(
        target=tqdm_converter,
        args=(len(json_data), images_converted, images_not_converted, finish_event),
        daemon=True,
    )
    logger.info("Converting to SuperAnnotate JSON format")
    tqdm_thread.start()
    for data in json_data:
        if "objects" not in data["Label"].keys():
            file_name = data["External ID"] + "___objects.json"
            write_to_json(
                output_dir / file_name,
                {"metadata": {}, "instances": [], "tags": [], "comments": []},
            )
            continue

        instances = data["Label"]["objects"]
        sa_instances = []

        for instance in instances:
            class_name = instance["value"]
            attributes = []
            if "classifications" in instance.keys():
                attributes = _create_attributes_list(instance["classifications"])

            lb_type = list(set(instance_types) & set(instance.keys()))
            if len(lb_type) != 1:
                continue

            if lb_type[0] == "bbox":
                points = (
                    instance["bbox"]["left"],
                    instance["bbox"]["top"],
                    instance["bbox"]["left"] + instance["bbox"]["width"],
                    instance["bbox"]["top"] + instance["bbox"]["height"],
                )
                instance_type = "bbox"
            elif lb_type[0] == "polygon":
                points = []
                for point in instance["polygon"]:
                    points.append(point["x"])
                    points.append(point["y"])
                instance_type = "polygon"
            elif lb_type[0] == "line":
                points = []
                for point in instance["line"]:
                    points.append(point["x"])
                    points.append(point["y"])
                instance_type = "polyline"
            elif lb_type[0] == "point":
                points = (instance["point"]["x"], instance["point"]["y"])
                instance_type = "point"

            sa_obj = _create_vector_instance(
                instance_type, points, {}, attributes, class_name
            )
            sa_instances.append(sa_obj)

        images_converted.append(data["External ID"])
        file_name = "%s___objects.json" % data["External ID"]
        try:
            img = cv2.imread(str(output_dir / data["External ID"]))
            H, W, _ = img.shape
        except Exception as e:
            logger.warning(
                "Can't open %s image. 'height' and 'width' for SA JSON metadata will set to zero",
                data["External ID"],
            )
            H, W = 0, 0

        sa_metadata = {"name": data["External ID"], "height": H, "width": W}
        sa_json = _create_sa_json(sa_instances, sa_metadata)
        write_to_json(output_dir / file_name, sa_json)

    finish_event.set()
    tqdm_thread.join()
    return classes
