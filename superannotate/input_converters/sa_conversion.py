import glob
import json
import logging
import os
import shutil
import time
from pathlib import Path

import cv2
import numpy as np
from tqdm import tqdm

from ..common import blue_color_generator, hex_to_rgb, rgb_to_hex

logger = logging.getLogger("superannotate-python-sdk")


def _merge_jsons(input_dir, output_dir):
    cat_id_map = {}
    classes_json = json.load(
        open(os.path.join(input_dir, "classes", "classes.json"))
    )

    new_classes = []
    for idx, class_ in enumerate(classes_json):
        cat_id_map[class_["id"]] = idx + 2
        class_["id"] = idx + 2
        new_classes.append(class_)

    files = glob.glob(os.path.join(input_dir, "*.json"))
    merged_json = {}
    os.makedirs(output_dir)
    for f in tqdm(files, "Merging files"):
        json_data = json.load(open(f))
        meta = {
            "type": "meta",
            "name": "lastAction",
            "timestamp": int(round(time.time() * 1000))
        }
        for js_data in json_data:
            if "classId" in js_data:
                js_data["classId"] = cat_id_map[js_data["classId"]]
        json_data.append(meta)
        file_name = os.path.split(f)[1].replace("___objects.json", "")
        merged_json[file_name] = json_data
    with open(
        os.path.join(output_dir, "annotations.json"), "w"
    ) as final_json_file:
        json.dump(merged_json, final_json_file, indent=2)

    with open(os.path.join(output_dir, "classes.json"), "w") as fw:
        json.dump(classes_json, fw, indent=2)


def _split_json(input_dir, output_dir):
    os.makedirs(output_dir)
    json_data = json.load(open(os.path.join(input_dir, "annotations.json")))
    for img, annotations in tqdm(json_data.items()):
        objects = []
        for annot in annotations:
            objects += annot

        with open(os.path.join(output_dir, img + "___objects.json"), "w") as fw:
            json.dump(objects, fw, indent=2)
    os.makedirs(os.path.join(output_dir, "classes"))
    shutil.copy(
        os.path.join(input_dir, "classes.json"),
        os.path.join(output_dir, "classes", "classes.json")
    )


def sa_convert_platform(input_dir, output_dir, input_platform):
    if input_platform == "Web":
        for file_name in os.listdir(input_dir):
            if '___pixel.json' in file_name:
                logging.error(
                    "Desktop platform doesn't support 'Pixel' projects"
                )
                break
        _merge_jsons(input_dir, output_dir)
    elif input_platform == 'Desktop':
        _split_json(input_dir, output_dir)
    else:
        logging.error("Please enter valid platform: 'Desktop' or 'Web'")


def from_pixel_to_vector(json_paths):
    sa_jsons = {}
    for json_path in json_paths:
        file_name = str(json_path.name
                       ).replace('___pixel.json', '___objects.json')

        mask_name = str(json_path).replace('___pixel.json', '___save.png')
        img = cv2.imread(mask_name)
        H, W, C = img.shape

        sa_loader = []
        instances = json.load(open(json_path))
        idx = 0
        for instance in instances:
            if 'parts' not in instance.keys():
                if 'type' in instance.keys() and instance['type'] == 'meta':
                    sa_loader.append(instance)
                continue

            parts = instance['parts']

            polygons = []
            for part in parts:
                color = list(hex_to_rgb(part['color']))
                mask = np.zeros((H, W), dtype=np.uint8)
                mask[np.all((img == color[::-1]), axis=2)] = 255
                contours, _ = cv2.findContours(
                    mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )
                part_polygons = []
                for contour in contours:
                    segment = contour.flatten().tolist()
                    if len(segment) > 6:
                        part_polygons.append(segment)
                polygons.append(part_polygons)

            for part_polygons in polygons:
                if len(part_polygons) > 1:
                    idx += 1
                    group_id = idx
                else:
                    group_id = 0

                for polygon in part_polygons:
                    temp = instance.copy()
                    del temp['parts']
                    temp['pointLabels'] = {}
                    temp['groupId'] = group_id
                    temp['type'] = 'polygon'
                    temp['points'] = polygon
                    sa_loader.append(temp.copy())
                    temp['type'] = 'bbox'
                    temp['points'] = {
                        'x1': min(polygon[::2]),
                        'x2': max(polygon[::2]),
                        'y1': min(polygon[1::2]),
                        'y2': max(polygon[1::2])
                    }
                    sa_loader.append(temp.copy())

        sa_jsons[file_name] = {'json': sa_loader, 'mask': None}
    return sa_jsons


def from_vector_to_pixel(json_paths):
    sa_jsons = {}
    for json_path in json_paths:
        file_name = str(json_path.name
                       ).replace('___objects.json', '___pixel.json')

        img_name = str(json_path).replace('___objects.json', '')
        img = cv2.imread(img_name)
        H, W, C = img.shape

        mask = np.zeros((H, W, 4))
        sa_loader = []

        instances = json.load(open(json_path))
        blue_colors = blue_color_generator(len(instances))
        instances_group = {}
        for idx, instance in enumerate(instances):
            if instance['type'] == 'polygon':
                if instance['groupId'] in instances_group.keys():
                    instances_group[instance['groupId']].append(instance)
                else:
                    instances_group[instance['groupId']] = [instance]
            elif instance['type'] == 'meta':
                sa_loader.append(instance)

        idx = 0
        for key, instances in instances_group.items():
            if key == 0:
                for instance in instances:
                    pts = np.array(
                        [
                            instance['points'][2 * i:2 * (i + 1)]
                            for i in range(len(instance['points']) // 2)
                        ],
                        dtype=np.int32
                    )
                    bitmask = np.zeros((H, W))
                    cv2.fillPoly(bitmask, [pts], 1)
                    mask[bitmask == 1
                        ] = list(hex_to_rgb(blue_colors[idx]))[::-1] + [255]
                    del instance['type']
                    del instance['points']
                    del instance['pointLabels']
                    del instance['groupId']
                    instance['parts'] = [{'color': blue_colors[idx]}]
                    sa_loader.append(instance.copy())
                    idx += 1
            else:
                parts = []
                for instance in instances:
                    pts = np.array(
                        [
                            instance['points'][2 * i:2 * (i + 1)]
                            for i in range(len(instance['points']) // 2)
                        ],
                        dtype=np.int32
                    )
                    bitmask = np.zeros((H, W))
                    cv2.fillPoly(bitmask, [pts], 1)
                    mask[bitmask == 1
                        ] = list(hex_to_rgb(blue_colors[idx]))[::-1] + [255]
                    parts.append({'color': blue_colors[idx]})
                    idx += 1
                del instance['type']
                del instance['points']
                del instance['pointLabels']
                del instance['groupId']
                instance['parts'] = parts
                sa_loader.append(instance.copy())

        sa_jsons[file_name] = {'json': sa_loader, 'mask': mask}

    return sa_jsons


def sa_convert_project_type(input_dir, output_dir):
    if type(input_dir) is str:
        input_dir = Path(input_dir)
    if type(output_dir) is str:
        output_dir = Path(output_dir)

    json_generator = input_dir.glob('*.json')
    json_paths = [file for file in json_generator]

    extension = ''
    if '___pixel.json' in json_paths[0].name:
        sa_jsons = from_pixel_to_vector(json_paths)
        extension = '___objects.json'
    elif '__objects.json' in json_paths[0].name:
        sa_jsons = from_vector_to_pixel(json_paths)
        extension = '___pixel.json'
    else:
        log_msg = "'input_dir' should contain JSON files with '[IMAGE_NAME]___objects.json'  or '[IMAGE_NAME]___pixel.json' names structure."
        raise SABaseException(0, log_msg)

    os.makedirs(output_dir.joinpath('classes'))
    shutil.copy(
        input_dir.joinpath('classes', 'classes.json'),
        output_dir.joinpath('classes', 'classes.json')
    )

    for key, value in sa_jsons.items():
        with open(output_dir.joinpath(key), 'w') as fw:
            json.dump(value['json'], fw, indent=2)
        file_name = key.replace(extension, '')
        shutil.copy(
            input_dir.joinpath(file_name), output_dir.joinpath(file_name)
        )

        if value['mask'] is not None:
            mask_name = key.replace(extension, '___save.png')
            cv2.imwrite(str(output_dir.joinpath(mask_name)), value['mask'])