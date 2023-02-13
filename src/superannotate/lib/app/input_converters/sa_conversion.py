import itertools
import json
import logging
import shutil

import cv2
import numpy as np
from lib.app.exceptions import AppException
from lib.core import DEPRICATED_DOCUMENT_VIDEO_MESSAGE

from ..common import blue_color_generator
from ..common import hex_to_rgb
from ..common import write_to_json

logger = logging.getLogger("sa")


def copy_file(src_path, dst_path):
    shutil.copy(src_path, dst_path)


def from_pixel_to_vector(json_paths, output_dir):
    img_names = []

    for json_path in json_paths:
        file_name = str(json_path.name).replace("___pixel.json", "___objects.json")

        mask_name = str(json_path).replace("___pixel.json", "___save.png")
        img = cv2.imread(mask_name)
        H, W, _ = img.shape
        sa_json = json.load(open(json_path))
        instances = sa_json["instances"]
        new_instances = []
        global_idx = itertools.count()
        sa_instances = []

        for instance in instances:
            if "parts" not in instance.keys():
                if "type" in instance.keys() and instance["type"] == "meta":
                    sa_instances.append(instance)
                continue
            parts = instance["parts"]
            if len(parts) > 1:
                group_id = next(global_idx)
            else:
                group_id = 0
            from collections import defaultdict

            for part in parts:
                color = list(hex_to_rgb(part["color"]))
                mask = np.zeros((H, W), dtype=np.uint8)
                mask[np.all((img == color[::-1]), axis=2)] = 255

                #  child contour index hierarchy[0][[i][3]
                contours, hierarchy = cv2.findContours(
                    mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
                )
                parent_child_map = defaultdict(list)
                for idx, _hierarchy in enumerate(hierarchy[0]):

                    if len(contours[idx].flatten().tolist()) <= 6:
                        continue
                    if _hierarchy[3] < 0:
                        parent_child_map[idx] = []
                    else:
                        parent_child_map[_hierarchy[3]].append(idx)

                for outer, inners in parent_child_map.items():
                    outer_points = contours[outer].flatten().tolist()
                    exclude_points = [contours[i].flatten().tolist() for i in inners]
                    temp = instance.copy()
                    del temp["parts"]
                    temp["pointLabels"] = {}
                    temp["groupId"] = group_id
                    temp["type"] = "polygon"
                    temp["points"] = outer_points
                    temp["exclude"] = exclude_points
                    new_instances.append(temp)

        sa_json["instances"] = new_instances
        write_to_json(output_dir / file_name, sa_json)
        img_names.append(file_name.replace("___objects.json", ""))
    return img_names


def from_vector_to_pixel(json_paths, output_dir):
    img_names = []
    for json_path in json_paths:
        file_name = str(json_path.name).replace("___objects.json", "___pixel.json")

        img_name = str(json_path).replace("___objects.json", "")
        img = cv2.imread(img_name)
        H, W, _ = img.shape

        sa_json = json.load(open(json_path))
        instances = sa_json["instances"]
        mask = np.zeros((H, W, 4))

        sa_instances = []
        blue_colors = blue_color_generator(len(instances))
        instances_group = {}
        for idx, instance in enumerate(instances):
            if instance["type"] == "polygon":
                if instance["groupId"] in instances_group.keys():
                    instances_group[instance["groupId"]].append(instance)
                else:
                    instances_group[instance["groupId"]] = [instance]
            elif instance["type"] == "meta":
                sa_instances.append(instance)

        idx = 0
        for key, instances in instances_group.items():
            if key == 0:
                for instance in instances:
                    pts = np.array(
                        [
                            instance["points"][2 * i : 2 * (i + 1)]
                            for i in range(len(instance["points"]) // 2)
                        ],
                        dtype=np.int32,
                    )
                    bitmask = np.zeros((H, W))
                    cv2.fillPoly(bitmask, [pts], 1)
                    mask[bitmask == 1] = list(hex_to_rgb(blue_colors[idx]))[::-1] + [
                        255
                    ]
                    del instance["type"]
                    del instance["points"]
                    del instance["pointLabels"]
                    del instance["groupId"]
                    instance["parts"] = [{"color": blue_colors[idx]}]
                    sa_instances.append(instance.copy())
                    idx += 1
            else:
                parts = []
                for instance in instances:
                    pts = np.array(
                        [
                            instance["points"][2 * i : 2 * (i + 1)]
                            for i in range(len(instance["points"]) // 2)
                        ],
                        dtype=np.int32,
                    )
                    bitmask = np.zeros((H, W))
                    cv2.fillPoly(bitmask, [pts], 1)
                    mask[bitmask == 1] = list(hex_to_rgb(blue_colors[idx]))[::-1] + [
                        255
                    ]
                    parts.append({"color": blue_colors[idx]})
                    idx += 1
                del instance["type"]
                del instance["points"]
                del instance["pointLabels"]
                del instance["groupId"]
                instance["parts"] = parts
                sa_instances.append(instance.copy())

        mask_name = file_name.replace("___pixel.json", "___save.png")
        cv2.imwrite(str(output_dir.joinpath(mask_name)), mask)

        sa_json["instances"] = sa_instances
        write_to_json(output_dir / file_name, sa_json)
        img_names.append(file_name.replace("___pixel.json", ""))
    return img_names


def sa_convert_project_type(input_dir, output_dir):
    json_paths = list(input_dir.glob("*.json"))

    output_dir.joinpath("classes").mkdir(parents=True)
    copy_file(
        input_dir.joinpath("classes", "classes.json"),
        output_dir.joinpath("classes", "classes.json"),
    )

    if "___pixel.json" in json_paths[0].name:
        img_names = from_pixel_to_vector(json_paths, output_dir)
    elif "___objects.json" in json_paths[0].name:
        img_names = from_vector_to_pixel(json_paths, output_dir)
    elif ".json" in json_paths[0].name:
        raise AppException(DEPRICATED_DOCUMENT_VIDEO_MESSAGE)
    else:
        raise AppException(
            "'input_dir' should contain JSON files with '[IMAGE_NAME]___objects.json' or '[IMAGE_NAME]___pixel.json' names structure.",
        )

    for img_name in img_names:
        copy_file(input_dir.joinpath(img_name), output_dir.joinpath(img_name))


def upgrade_json(input_dir, output_dir):
    files_list = list(input_dir.glob("*.json"))
    ptype = "Vector"
    if "___pixel" in str(files_list[0].name):
        ptype = "Pixel"

    converted_files = []
    failed_files = []
    for file in files_list:
        file_name = file.name
        try:
            output_json = _update_json_format(file, ptype)
            converted_files.append(file_name)
            write_to_json(output_dir / file_name, output_json)
        except Exception as e:
            logger.debug(str(e), exc_info=True)
            failed_files.append(file_name)

    return converted_files


def degrade_json(input_dir, output_dir):
    files_list = list(input_dir.glob("*.json"))

    converted_files = []
    failed_files = []
    for file in files_list:
        file_name = file.name
        try:
            output_json = _degrade_json_format(file)
            converted_files.append(output_dir / file_name)
            write_to_json(output_dir / file_name, output_json)
        except Exception as e:
            failed_files.append(file_name)

    return converted_files


def _update_json_format(old_json_path, project_type):
    old_json_data = json.load(open(old_json_path))
    new_json_data = {"metadata": {}, "instances": [], "tags": [], "comments": []}

    meta_keys = [
        "name",
        "width",
        "height",
        "status",
        "pinned",
        "isPredicted",
        "projectId",
        "annotatorEmail",
        "qaEmail",
    ]
    if project_type == "Pixel":
        meta_keys.append("isSegmented")

    new_json_data["metadata"] = dict.fromkeys(meta_keys)

    suffix = "___objects.json" if project_type == "Vector" else "___pixel.json"
    image_name = str(old_json_path.name).split(suffix)[0]
    metadata = new_json_data["metadata"]
    metadata["name"] = image_name

    for item in old_json_data:
        object_type = item.get("type")
        if object_type == "meta":
            meta_name = item["name"]
            if meta_name == "imageAttributes":
                metadata["height"] = item.get("height")
                metadata["width"] = item.get("width")
                metadata["status"] = item.get("status")
                metadata["pinned"] = item.get("pinned")
            if meta_name == "lastAction":
                metadata["lastAction"] = dict.fromkeys(["email", "timestamp"])
                metadata["lastAction"]["email"] = item.get("userId")
                metadata["lastAction"]["timestamp"] = item.get("timestamp")
        elif object_type == "tag":
            new_json_data["tags"].append(item.get("name"))
        elif object_type == "comment":
            item.pop("type")
            item["correspondence"] = item["comments"]
            for comment in item["correspondence"]:
                comment["email"] = comment["id"]
                comment.pop("id")
            item.pop("comments")
            new_json_data["comments"].append(item)
        else:
            new_json_data["instances"].append(item)

    return new_json_data


def _degrade_json_format(new_json_path):
    sa_loader = []
    new_json_data = json.load(open(new_json_path))

    meta = {"type": "meta", "name": "imageAttributes"}
    meta_keys = ["height", "width", "status", "pinned"]
    for meta_key in meta_keys:
        if meta_key in new_json_data["metadata"]:
            meta[meta_key] = new_json_data["metadata"][meta_key]
    sa_loader.append(meta)

    if "lastAction" in new_json_data["metadata"]:
        meta = {
            "type": "meta",
            "name": "lastAction",
            "userId": new_json_data["metadata"]["lastAction"]["email"],
            "timestamp": new_json_data["metadata"]["lastAction"]["timestamp"],
        }
        sa_loader.append(meta)

    for item in new_json_data["instances"]:
        sa_loader.append(item)

    for item in new_json_data["comments"]:
        comments = []
        for item2 in item["correspondence"]:
            comments.append({"text": item2["text"], "id": item2["email"]})
            item["comments"] = comments
        item["createdAt"] = item["correspondence"][0]["timestamp"]
        item["createdBy"] = {
            "email": item["correspondence"][0]["email"],
            "role": item["correspondence"][0]["role"],
        }
        item["updatedAt"] = item["correspondence"][-1]["timestamp"]
        item["updatedBy"] = {
            "email": item["correspondence"][-1]["email"],
            "role": item["correspondence"][-1]["role"],
        }
        item.pop("correspondence")
        item["type"] = "comment"
        item["comments"] = comments
        sa_loader.append(item)

    for item in new_json_data["tags"]:
        tag = {"type": "tag", "name": item}
        sa_loader.append(tag)

    return sa_loader
