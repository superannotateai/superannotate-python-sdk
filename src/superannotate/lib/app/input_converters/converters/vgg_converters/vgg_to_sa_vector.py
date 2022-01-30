"""
VGG to SA conversion method.
"""
import json
import threading

import cv2
from superannotate.logger import get_default_logger

from ....common import tqdm_converter
from ....common import write_to_json
from ..sa_json_helper import _create_sa_json
from ..sa_json_helper import _create_vector_instance
from .vgg_helper import _create_attribute_list

logger = get_default_logger()


def vgg_to_sa(json_data, task, output_dir):
    images = json.load(open(json_data))
    if task == "object_detection":
        instance_types = ["rect"]
    elif task == "instance_segmentation":
        instance_types = ["polygon"]
    elif task == "vector_annotation":
        instance_types = ["rect", "polygon", "polyline", "point", "ellipse", "circle"]

    images_converted = []
    images_not_converted = []
    finish_event = threading.Event()
    tqdm_thread = threading.Thread(
        target=tqdm_converter,
        args=(
            len(images.items()),
            images_converted,
            images_not_converted,
            finish_event,
        ),
        daemon=True,
    )
    logger.info("Converting to SuperAnnotate JSON format")
    tqdm_thread.start()

    class_id_map = {}
    for _, img in images.items():
        try:
            H, W, _ = cv2.imread(str(output_dir / img["filename"])).shape
        except Exception:
            logger.warning(
                "Can't open %s image. 'height' and 'width' for SA JSON metadata will set to zero",
                img["filename"],
            )
            H = 0
            W = 0

        file_name = "%s___objects.json" % img["filename"]
        sa_metadata = {"name": img["filename"], "width": W, "height": H}
        sa_instances = []
        instances = img["regions"]
        for instance in instances:
            if "type" not in instance["region_attributes"].keys():
                raise KeyError(
                    "'VGG' JSON should contain 'type' key which will \
                    be category name. Please correct JSON file."
                )
            if not isinstance(instance["region_attributes"]["type"], str):
                raise ValueError("Wrong attribute was choosen for 'type' attribute.")

            class_name = instance["region_attributes"]["type"]
            if class_name not in class_id_map.keys():
                class_id_map[class_name] = {"attribute_groups": {}}

            attributes = _create_attribute_list(
                instance["region_attributes"], class_name, class_id_map
            )

            if instance["shape_attributes"]["name"] in instance_types:
                if (
                    instance["shape_attributes"]["name"] == "polygon"
                    or instance["shape_attributes"]["name"] == "polyline"
                ):
                    points = []
                    for x, y in zip(
                        instance["shape_attributes"]["all_points_x"],
                        instance["shape_attributes"]["all_points_y"],
                    ):
                        points.append(x)
                        points.append(y)
                    instance_type = instance["shape_attributes"]["name"]
                elif instance["shape_attributes"]["name"] == "rect":
                    points = (
                        instance["shape_attributes"]["x"],
                        instance["shape_attributes"]["y"],
                        instance["shape_attributes"]["x"]
                        + instance["shape_attributes"]["width"],
                        instance["shape_attributes"]["y"]
                        + instance["shape_attributes"]["height"],
                    )
                    instance_type = "bbox"
                elif instance["shape_attributes"]["name"] == "ellipse":
                    points = (
                        instance["shape_attributes"]["cx"],
                        instance["shape_attributes"]["cy"],
                        instance["shape_attributes"]["rx"],
                        instance["shape_attributes"]["ry"],
                        instance["shape_attributes"]["theta"],
                    )
                    instance_type = "ellipse"
                elif instance["shape_attributes"]["name"] == "circle":
                    points = (
                        instance["shape_attributes"]["cx"],
                        instance["shape_attributes"]["cy"],
                        instance["shape_attributes"]["r"],
                        instance["shape_attributes"]["r"],
                        0,
                    )
                    instance_type = "ellipse"
                elif instance["shape_attributes"]["name"] == "point":
                    points = (
                        instance["shape_attributes"]["cx"],
                        instance["shape_attributes"]["cy"],
                    )
                    instance_type = "point"
                sa_obj = _create_vector_instance(
                    instance_type, points, {}, attributes, class_name
                )
                sa_instances.append(sa_obj)
        images_converted.append(img["filename"])
        sa_json = _create_sa_json(sa_instances, sa_metadata)
        write_to_json(output_dir / file_name, sa_json)
    finish_event.set()
    tqdm_thread.join()
    return class_id_map
