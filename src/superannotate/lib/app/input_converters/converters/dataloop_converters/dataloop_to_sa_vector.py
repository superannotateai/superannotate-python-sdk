"""
Dataloop to SA conversion method
"""
import json
import logging
import threading

from ....common import tqdm_converter
from ....common import write_to_json
from ..sa_json_helper import _create_comment
from ..sa_json_helper import _create_sa_json
from ..sa_json_helper import _create_vector_instance
from .dataloop_helper import _create_attributes_list
from .dataloop_helper import _update_classes_dict

logger = logging.getLogger("sa")


def dataloop_to_sa(input_dir, task, output_dir):
    classes = {}
    json_data = list(input_dir.glob("*.json"))
    if task == "object_detection":
        instance_types = ["box"]
    elif task == "instance_segmentation":
        instance_types = ["segment"]
    elif task == "vector_annotation":
        instance_types = ["point", "box", "ellipse", "segment"]

    tags_type = "class"
    comment_type = "note"

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
    for json_file in json_data:
        dl_data = json.load(open(json_file))

        sa_metadata = {}
        if "itemMetadata" in dl_data and "system" in dl_data["itemMetadata"]:
            temp = dl_data["itemMetadata"]["system"]
            sa_metadata["name"] = temp["originalname"]
            sa_metadata["width"] = temp["width"]
            sa_metadata["height"] = temp["height"]

        sa_instances = []
        sa_tags = []
        sa_comments = []

        for ann in dl_data["annotations"]:
            if ann["type"] in instance_types:
                classes = _update_classes_dict(classes, ann["label"], ann["attributes"])

            attributes = _create_attributes_list(ann["attributes"])

            if ann["type"] in instance_types:
                if ann["type"] == "segment" and len(ann["coordinates"]) == 1:
                    points = []
                    for sub_list in ann["coordinates"]:
                        for sub_dict in sub_list:
                            points.append(sub_dict["x"])
                            points.append(sub_dict["y"])
                    instance_type = "polygon"
                elif ann["type"] == "box":
                    points = (
                        ann["coordinates"][0]["x"],
                        ann["coordinates"][0]["y"],
                        ann["coordinates"][1]["x"],
                        ann["coordinates"][1]["y"],
                    )
                    instance_type = "bbox"
                elif ann["type"] == "ellipse":
                    points = (
                        ann["coordinates"]["center"]["x"],
                        ann["coordinates"]["center"]["y"],
                        ann["coordinates"]["rx"],
                        ann["coordinates"]["ry"],
                        ann["coordinates"]["angle"],
                    )
                    instance_type = "ellipse"
                elif ann["type"] == "point":
                    points = (ann["coordinates"]["x"], ann["coordinates"]["y"])
                    instance_type = "point"
                sa_obj = _create_vector_instance(
                    instance_type, points, {}, attributes, ann["label"]
                )
                sa_instances.append(sa_obj)
            elif ann["type"] == comment_type:
                points = (
                    ann["coordinates"]["box"][0]["x"],
                    ann["coordinates"]["box"][0]["y"],
                )
                comments = []
                for note in ann["coordinates"]["note"]["messages"]:
                    comments.append({"text": note["body"], "email": note["creator"]})
                    sa_comment = _create_comment(points, comments)
                sa_comments.append(sa_comment)
            elif ann["type"] == tags_type:
                sa_tags.append(ann["label"])

        if "name" in sa_metadata:
            file_name = "%s___objects.json" % sa_metadata["name"]
        else:
            file_name = "%s___objects.json" % dl_data["filename"][1:]

        images_converted.append(file_name.replace("___objects.json ", ""))
        json_template = _create_sa_json(sa_instances, sa_metadata, sa_tags, sa_comments)
        write_to_json(output_dir / file_name, json_template)
    finish_event.set()
    tqdm_thread.join()
    return classes
