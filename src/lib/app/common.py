import functools
import json
import logging
import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image
from tqdm import tqdm

logger = logging.getLogger("superannotate-python-sdk")

DEFAULT_IMAGE_EXTENSIONS = ("jpg", "jpeg", "png", "tif", "tiff", "webp", "bmp")
DEFAULT_FILE_EXCLUDE_PATTERNS = ("___save.png", "___fuse.png")

DEFAULT_VIDEO_EXTENSIONS = ("mp4", "avi", "mov", "webm", "flv", "mpg", "ogg")

SPECIAL_CHARACTERS_IN_PROJECT_FOLDER_NAMES = set('/\\:*?"<>|')

_PROJECT_TYPES = {"Vector": 1, "Pixel": 2}

_ANNOTATION_STATUSES = {
    "NotStarted": 1,
    "InProgress": 2,
    "QualityCheck": 3,
    "Returned": 4,
    "Completed": 5,
    "Skipped": 6
}

_UPLOAD_STATES_STR_TO_CODES = {"Initial": 1, "Basic": 2, "External": 3}
_UPLOAD_STATES_CODES_TO_STR = {1: "Initial", 2: "Basic", 3: "External"}

_USER_ROLES = {"Admin": 2, "Annotator": 3, "QA": 4, "Customer": 5, "Viewer": 6}
_AVAILABLE_SEGMENTATION_MODELS = ['autonomous', 'generic']
_MODEL_TRAINING_STATUSES = {
    "NotStarted": 1,
    "InProgress": 2,
    "Completed": 3,
    "FailedBeforeEvaluation": 4,
    "FailedAfterEvaluation": 5,
    "FailedAfterEvaluationWithSavedModel": 6
}

_PREDICTION_SEGMENTATION_STATUSES = {
    "NotStarted": 1,
    "InProgress": 2,
    "Completed": 3,
    "Failed": 4
}

_MODEL_TRAINING_TASKS = {
    "Instance Segmentation for Pixel Projects": "instance_segmentation_pixel",
    "Instance Segmentation for Vector Projects": "instance_segmentation_vector",
    "Keypoint Detection for Vector Projects": "keypoint_detection_vector",
    "Object Detection for Vector Projects": "object_detection_vector",
    "Semantic Segmentation for Pixel Projects": "semantic_segmentation_pixel"
}


def prediction_segmentation_status_from_str_to_int(status):
    return _PREDICTION_SEGMENTATION_STATUSES[status]


def prediction_segmentation_status_from_int_to_str(status):
    for idx, item in _PREDICTION_SEGMENTATION_STATUSES.items():
        if item == status:
            return idx
    raise RuntimeError("NA segmentation/prediction status")


def model_training_status_int_to_str(project_status):
    for item in _MODEL_TRAINING_STATUSES:
        if _MODEL_TRAINING_STATUSES[item] == project_status:
            return item
    raise RuntimeError("NA training status")


def model_training_status_str_to_int(project_status):
    return _MODEL_TRAINING_STATUSES[project_status]


def image_path_to_annotation_paths(image_path, project_type):
    image_path = Path(image_path)
    if project_type == "Vector":
        return (
            image_path.parent /
            get_annotation_json_name(image_path.name, project_type),
        )
    return (
        image_path.parent /
        get_annotation_json_name(image_path.name, project_type),
        image_path.parent / get_annotation_png_name(image_path.name)
    )


def project_type_str_to_int(project_type):
    return _PROJECT_TYPES[project_type]


def project_type_int_to_str(project_type):
    """Converts metadata project_type int value to a string

    :param project_type: int in project metadata's 'type' key
    :type project_type: int

    :return: 'Vector' or 'Pixel'
    :rtype: str
    """
    for k, v in _PROJECT_TYPES.items():
        if v == project_type:
            return k
    raise RuntimeError("NA Project type")


def user_role_str_to_int(user_role):
    return _USER_ROLES[user_role]


def user_role_int_to_str(user_role):
    for k, v in _USER_ROLES.items():
        if v == user_role:
            return k
    return None


def annotation_status_str_to_int(annotation_status):
    return _ANNOTATION_STATUSES[annotation_status]


def upload_state_str_to_int(upload_state):
    return _UPLOAD_STATES_STR_TO_CODES[upload_state]


def upload_state_int_to_str(upload_state):
    return _UPLOAD_STATES_CODES_TO_STR[upload_state]


def annotation_status_int_to_str(annotation_status):
    """Converts metadata annotation_status int value to a string

    :param annotation_status: int in image metadata's 'annotation_status' key
    :type annotation_status: int

    :return: One of 'NotStarted' 'InProgress' 'QualityCheck' 'Returned' 'Completed' 'Skipped'
    :rtype: str
    """

    for k, v in _ANNOTATION_STATUSES.items():
        if v == annotation_status:
            return k
    return None


def deprecated_alias(**aliases):
    def deco(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            rename_kwargs(f.__name__, kwargs, aliases)
            return f(*args, **kwargs)

        return wrapper

    return deco


def rename_kwargs(func_name, kwargs, aliases):
    for alias, new in aliases.items():
        if alias in kwargs:
            if new in kwargs:
                raise TypeError(
                    '{} received both {} and {}'.format(func_name, alias, new)
                )
            logger.warning(
                '%s is deprecated; use %s in %s', alias, new, func_name
            )
            kwargs[new] = kwargs.pop(alias)


def hex_to_rgb(hex_string):
    """Converts HEX values to RGB values
    """
    h = hex_string.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb_tuple):
    """Converts RGB values to HEX values
    """
    return '#%02x%02x%02x' % rgb_tuple


def blue_color_generator(n, hex_values=True):
    """ Blue colors generator for SuperAnnotate blue mask.
    """
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
        cat_id_map[class_['name']] = idx + 2
        class_['id'] = idx + 2
        new_classes.append(class_)
    with open(output_dir.joinpath('classes.json'), 'w') as fw:
        json.dump(new_classes, fw)

    meta = {
        "type": "meta",
        "name": "lastAction",
        "timestamp": int(round(time.time() * 1000))
    }
    new_json = {}
    files_path = []
    (output_dir / 'images' / 'thumb').mkdir()
    for file_name, json_data in files_dict.items():
        file_name = file_name.replace('___objects.json', '')
        if not (output_dir / 'images' / file_name).exists():
            continue

        for js_data in json_data:
            if 'className' in js_data:
                js_data['classId'] = cat_id_map[js_data['className']]
        json_data.append(meta)
        new_json[file_name] = json_data

        files_path.append(
            {
                'srcPath':
                    str(output_dir.resolve() / file_name),
                'name':
                    file_name,
                'imagePath':
                    str(output_dir.resolve() / file_name),
                'thumbPath':
                    str(
                        output_dir.resolve() / 'images' / 'thumb' /
                        ('thmb_' + file_name + '.jpg')
                    ),
                'valid':
                    True
            }
        )

        img = Image.open(output_dir / 'images' / file_name)
        img.thumbnail((168, 120), Image.ANTIALIAS)
        img.save(
            output_dir / 'images' / 'thumb' / ('thmb_' + file_name + '.jpg')
        )

    with open(output_dir / 'images' / 'images.sa', 'w') as fw:
        fw.write(json.dumps(files_path))

    with open(output_dir.joinpath('annotations.json'), 'w') as fw:
        json.dump(new_json, fw)

    with open(output_dir / 'config.json', 'w') as fw:
        json.dump({"pathSeparator": os.sep, "os": sys.platform}, fw)


def save_web_format(output_dir, classes, files_dict):
    for key, value in files_dict.items():
        with open(output_dir.joinpath(key), 'w') as fw:
            json.dump(value, fw, indent=2)

    with open(output_dir.joinpath('classes', 'classes.json'), 'w') as fw:
        json.dump(classes, fw)


def dump_output(output_dir, platform, classes, files_dict):
    if platform == 'Web':
        save_web_format(output_dir, classes, files_dict)
    else:
        save_desktop_format(output_dir, classes, files_dict)


def write_to_json(output_path, json_data):
    with open(output_path, 'w') as fw:
        json.dump(json_data, fw, indent=2)


MAX_IMAGE_SIZE = 100 * 1024 * 1024  # 100 MB limit
MAX_IMAGE_RESOLUTION = {
    "Vector": 100_000_000,
    "Pixel": 4_000_000
}  # Resolution limit


def tqdm_converter(
    total_num, images_converted, images_not_converted, finish_event
):
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
