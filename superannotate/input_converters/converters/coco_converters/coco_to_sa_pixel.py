import os
import json

import cv2
import numpy as np

from panopticapi.utils import id2rgb
from tqdm import tqdm


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
    for i in range(n):
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
    return hex_colors


def coco_panoptic_segmentation_to_sa_pixel(coco_path, images_path):
    coco_json = json.load(open(coco_path))
    hex_colors = _blue_color_generator(len(coco_json["categories"]))
    annotate_list = coco_json["annotations"]

    for annotate in tqdm(annotate_list, "Converting"):
        annot_name = os.path.splitext(annotate["file_name"])[0]
        img_cv = cv2.imread(os.path.join(images_path, annot_name + ".png"))
        if img_cv is None:
            print(
                "'{}' file dosen't exist!".format(
                    os.path.join(images_path, annot_name + ".png")
                )
            )
            continue

        img = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
        H, W, C = img.shape
        img = img.reshape((H * W, C))
        segments = annotate["segments_info"]
        hex_colors = _blue_color_generator(len(segments) + 1)

        out_json = []
        for i, seg in enumerate(segments):
            img[np.all(img == id2rgb(seg["id"]),
                       axis=1)] = _hex_to_rgb(hex_colors[i + 1])
            dd = {
                "classId": seg["category_id"],
                "probability": 100,
                "visible": True,
                "parts": [{
                    "color": hex_colors[i + 1]
                }],
                "attributes": [],
                "attributeNames": [],
                "imageId": annotate["image_id"]
            }
            out_json.append(dd)

        with open(
            os.path.join(images_path, annot_name + ".jpg___pixel.json"), "w"
        ) as writer:
            json.dump(out_json, writer, indent=2)

        img = cv2.cvtColor(img.reshape((H, W, C)), cv2.COLOR_RGB2BGR)
        cv2.imwrite(
            os.path.join(images_path, annot_name + ".jpg___save.png"), img
        )

        os.remove(os.path.join(images_path, annot_name + ".png"))
