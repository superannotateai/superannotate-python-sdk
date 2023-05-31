import itertools
import json
import logging
import shutil
from pathlib import Path

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
        file_name = str(json_path)
        pixel_postfix = "___pixel.json"
        postfix = pixel_postfix if file_name.endswith(pixel_postfix) else ".json"
        mask_name = file_name.replace(postfix, "___save.png")
        img = cv2.imread(mask_name)
        H, W, _ = img.shape
        sa_json = json.load(open(file_name))
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
        write_to_json(
            str(output_dir / Path(file_name).name.replace(postfix, ".json")), sa_json
        )
        img_names.append(file_name.replace(postfix, ""))
    return img_names


def from_vector_to_pixel(json_paths, output_dir):
    img_names = []
    for json_path in json_paths:
        file_name = str(json_path)
        vector_postfix = "___objects.json"
        postfix = vector_postfix if file_name.endswith(vector_postfix) else ".json"
        img_name = file_name.replace(postfix, "")
        img = cv2.imread(img_name)
        H, W, _ = img.shape

        sa_json = json.load(open(file_name))
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

        mask_name = file_name.replace(postfix, "___save.png")
        cv2.imwrite(str(output_dir.joinpath(Path(mask_name).name)), mask)

        sa_json["instances"] = sa_instances
        write_to_json(
            str(output_dir / Path(file_name).name.replace(postfix, ".json")), sa_json
        )
        img_names.append(img_name.replace(".json", ""))
    return img_names


def sa_convert_project_type(input_dir, output_dir, convert_to):
    json_paths = list(input_dir.glob("*.json"))

    output_dir.joinpath("classes").mkdir(parents=True)
    copy_file(
        input_dir.joinpath("classes", "classes.json"),
        output_dir.joinpath("classes", "classes.json"),
    )

    if convert_to == "Vector":
        img_names = from_pixel_to_vector(json_paths, output_dir)
    elif convert_to == "Pixel":
        img_names = from_vector_to_pixel(json_paths, output_dir)
    else:
        raise AppException(DEPRICATED_DOCUMENT_VIDEO_MESSAGE)

    for img_name in img_names:
        copy_file(img_name, output_dir / Path(img_name).name)
