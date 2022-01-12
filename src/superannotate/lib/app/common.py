import json
import os
import sys
import time

import numpy as np
from PIL import Image
from superannotate.logger import get_default_logger
from tqdm import tqdm

logger = get_default_logger()

_PROJECT_TYPES = {"Vector": 1, "Pixel": 2}

_ANNOTATION_STATUSES = {
    "NotStarted": 1,
    "InProgress": 2,
    "QualityCheck": 3,
    "Returned": 4,
    "Completed": 5,
    "Skipped": 6,
}


def hex_to_rgb(hex_string):
    """Converts HEX values to RGB values
    """
    h = hex_string.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def blue_color_generator(n, hex_values=True):
    """ Blue colors generator for SuperAnnotate blue mask.
    """
    hex_colors = []
    for i in range(n + 1):
        int_color = i * 15
        bgr_color = np.array(
            [int_color & 255, (int_color >> 8) & 255, (int_color >> 16) & 255, 255],
            dtype=np.uint8,
        )
        hex_color = (
            "#"
            + "{:02x}".format(bgr_color[2])
            + "{:02x}".format(bgr_color[1],)
            + "{:02x}".format(bgr_color[0])
        )
        if hex_values:
            hex_colors.append(hex_color)
        else:
            hex_colors.append(hex_to_rgb(hex_color))
    return hex_colors[1:]


def id2rgb(id_map):
    if isinstance(id_map, np.ndarray):
        id_map_copy = id_map.copy()
        rgb_shape = tuple(list(id_map.shape) + [3])
        rgb_map = np.zeros(rgb_shape, dtype=np.uint8)
        for i in range(3):
            rgb_map[..., i] = id_map_copy % 256
            id_map_copy //= 256
        return rgb_map
    color = []
    for _ in range(3):
        color.append(id_map % 256)
        id_map //= 256
    return color


def save_desktop_format(output_dir, classes, files_dict):
    cat_id_map = {}
    new_classes = []
    for idx, class_ in enumerate(classes):
        cat_id_map[class_["name"]] = idx + 2
        class_["id"] = idx + 2
        new_classes.append(class_)
    with open(output_dir.joinpath("classes.json"), "w") as fw:
        json.dump(new_classes, fw)

    meta = {
        "type": "meta",
        "name": "lastAction",
        "timestamp": int(round(time.time() * 1000)),
    }
    new_json = {}
    files_path = []
    (output_dir / "images" / "thumb").mkdir()
    for file_name, json_data in files_dict.items():
        file_name = file_name.replace("___objects.json", "")
        if not (output_dir / "images" / file_name).exists():
            continue

        for js_data in json_data:
            if "className" in js_data:
                js_data["classId"] = cat_id_map[js_data["className"]]
        json_data.append(meta)
        new_json[file_name] = json_data

        files_path.append(
            {
                "srcPath": str(output_dir.resolve() / file_name),
                "name": file_name,
                "imagePath": str(output_dir.resolve() / file_name),
                "thumbPath": str(
                    output_dir.resolve()
                    / "images"
                    / "thumb"
                    / ("thmb_" + file_name + ".jpg")
                ),
                "valid": True,
            }
        )

        img = Image.open(output_dir / "images" / file_name)
        img.thumbnail((168, 120), Image.ANTIALIAS)
        img.save(output_dir / "images" / "thumb" / ("thmb_" + file_name + ".jpg"))

    with open(output_dir / "images" / "images.sa", "w") as fw:
        fw.write(json.dumps(files_path))

    with open(output_dir.joinpath("annotations.json"), "w") as fw:
        json.dump(new_json, fw)

    with open(output_dir / "config.json", "w") as fw:
        json.dump({"pathSeparator": os.sep, "os": sys.platform}, fw)


def save_web_format(output_dir, classes, files_dict):
    for key, value in files_dict.items():
        with open(output_dir.joinpath(key), "w") as fw:
            json.dump(value, fw, indent=2)

    with open(output_dir.joinpath("classes", "classes.json"), "w") as fw:
        json.dump(classes, fw)


def write_to_json(output_path, json_data):
    with open(output_path, "w") as fw:
        json.dump(json_data, fw, indent=2)


MAX_IMAGE_SIZE = 100 * 1024 * 1024  # 100 MB limit


def tqdm_converter(total_num, images_converted, images_not_converted, finish_event):
    with tqdm(total=total_num) as pbar:
        while True:
            finished = finish_event.wait(5)
            if not finished:
                sum_all = len(images_converted) + len(images_not_converted)
                pbar.update(sum_all - pbar.n)
            else:
                pbar.update(total_num - pbar.n)
                break


def get_annotation_json_name(image_name, project_type):
    if project_type == "Vector":
        return image_name + "___objects.json"
    else:
        return image_name + "___pixel.json"


def get_annotation_png_name(image_name):
    return image_name + "___save.png"
