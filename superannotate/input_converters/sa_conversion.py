import glob
import json
import logging
import os
import shutil
import time
import cv2
import numpy as np

from tqdm import tqdm
from pathlib import Path


# Converts HEX values to RGB values
def _hex_to_rgb(hex_string):
    h = hex_string.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# Converts RGB values to HEX values
def _rgb_to_hex(rgb_tuple):
    return '#%02x%02x%02x' % rgb_tuple


# Generates blue colors in range(n)
def _blue_color_generator(n, hex_values=True):
    hex_colors = []
    for i in range(n + 1):
        int_color = i * 15
        bgr_color = np.array(
            [
                int_color & 255, (int_color >> 8) & 255,
                (int_color >> 16) & 255, 255
            ],
            dtype=np.uint8
        )
        hex_color = '#' + "{:02x}".format(
            bgr_color[2]
        ) + "{:02x}".format(bgr_color[1], ) + "{:02x}".format(bgr_color[0])
        if hex_values:
            hex_colors.append(hex_color)
        else:
            hex_colors.append(_hex_to_rgb(hex_color))
    return hex_colors[1:]


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
    images = json_data.keys()
    for img in images:
        annotations = json_data[img]
        objects = []
        for annot in annotations:
            objects.append(annot)

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
        mask = np.zeros((H, W), dtype=np.uint8)

        sa_loader = []
        instances = json.load(open(json_path))
        idx = 0
        group_id_map = {}
        for instance in instances:
            parts = instance['parts']
            if len(parts) > 1:
                idx += 1
                group_id = idx
            else:
                group_id = 0

            if group_id not in group_id_map.keys():
                group_id_map[group_id] = []

            for part in parts:
                color = list(_hex_to_rgb(part['color']))
                mask[np.all((img == color[::-1]), axis=2)] = 255
                contours, _ = cv2.findContours(
                    mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )
                if len(contours) > 0:
                    idx += 1
                    group_id = idx

                if group_id not in group_id_map.keys():
                    group_id_map[group_id] = []

                for contour in contours:
                    segment = contour.flatten().tolist()
                    group_id_map[group_id].append(segment)

        temp = instance.copy()
        del temp['parts']
        temp['pointLabels'] = {}

        for key, value in group_id_map.items():
            for polygon in value:
                temp['groupId'] = key
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
        blue_colors = _blue_color_generator(len(instances))
        group_id_map = {}
        for idx, instance in enumerate(instances):
            if instance['type'] == 'polygon':
                pts = np.array(
                    [
                        instance['points'][2 * i:2 * (i + 1)]
                        for i in range(len(instance['points']) // 2)
                    ],
                    dtype=np.int32
                )

                if instance['groupId'] in group_id_map.keys():
                    group_id_map[instance['groupId']].append(pts)
                else:
                    group_id_map[instance['groupId']] = [pts]

        temp = instance.copy()
        del temp['type']
        del temp['points']
        del temp['pointLabels']
        del temp['groupId']

        temp['parts'] = []
        idx = 0
        for key, values in group_id_map.items():
            if key == 0:
                for polygon in values:
                    bitmask = np.zeros((H, W))
                    cv2.fillPoly(bitmask, [polygon], 1)
                    mask[bitmask == 1
                        ] = list(_hex_to_rgb(blue_colors[idx]))[::-1] + [255]
                    temp['parts'].append({'color': blue_colors[idx]})
                    sa_loader.append(temp.copy())
                    idx += 1
            else:
                for polygon in values:
                    bitmask = np.zeros((H, W))
                    cv2.fillPoly(bitmask, [polygon], 1)
                    mask[bitmask == 1
                        ] = list(_hex_to_rgb(blue_colors[idx]))[::-1] + [255]
                    temp['parts'].append({'color': blue_colors[idx]})
                    idx += 1
                sa_loader.append(temp.copy())

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