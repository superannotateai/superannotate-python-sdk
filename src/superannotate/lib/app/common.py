import json

import numpy as np
from superannotate.logger import get_default_logger
from tqdm import tqdm

logger = get_default_logger()


def hex_to_rgb(hex_string):
    """Converts HEX values to RGB values"""
    h = hex_string.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def blue_color_generator(n, hex_values=True):
    """Blue colors generator for SuperAnnotate blue mask."""
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
            + "{:02x}".format(
                bgr_color[1],
            )
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
