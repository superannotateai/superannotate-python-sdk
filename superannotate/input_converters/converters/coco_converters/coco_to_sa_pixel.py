import json
import os

import cv2
import numpy as np
import pycocotools.mask as maskUtils
from panopticapi.utils import id2rgb
from tqdm import tqdm

from ....common import hex_to_rgb

# def _rle_to_bitmask(coco_json, annotation):
#     return coco.annToMask(annotation)


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
            hex_colors.append(hex_to_rgb(hex_color))
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
                       axis=1)] = hex_to_rgb(hex_colors[i + 1])
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


def coco_instance_segmentation_to_sa_pixel(coco_path, images_path):
    coco_json = json.load(open(coco_path))
    image_id_to_annotations = {}
    cat_id_to_cat = {}
    for cat in coco_json['categories']:
        cat_id_to_cat[cat['id']] = cat

    images_dict = {}
    for img in coco_json['images']:
        images_dict[img['id']] = {
            'mask': np.zeros((img['height'], img['width'], 4)),
            'file_name': img['file_name'],
            'segments_num': 0
        }

    sa_json = {}
    for annot in tqdm(coco_json['annotations'], "Convertring annotations"):
        if str(annot['image_id']) not in images_dict:
            continue
        color = np.random.choice(range(256), size=3)
        hexcolor = "#%02x%02x%02x" % tuple(color)

        images_dict[str(annot['image_id']
                       )]['mask'][maskUtils.decode(annot['segmentation']) == 1
                                 ] = list(color)[::-1] + [255]

        sa_obj = {
            "classId": annot['category_id'],
            "className": cat_id_to_cat[annot['category_id']]['name'],
            'probability': 100,
            'visible': True,
            'parts': [{
                'color': hexcolor
            }],
            "attributes": [],
            "attributeNames": [],
            "imageId": annot["image_id"]
        }
        key = images_dict[str(annot['image_id'])]['file_name']
        if key not in sa_json.keys():
            sa_json[key] = []

        sa_json[key].append(sa_obj)

    for id_, value in images_dict.items():
        img = cv2.imwrite(
            os.path.join(images_path, value['file_name'] + '___save.png'),
            value['mask']
        )

    for key, sa_js in sa_json.items():
        with open(os.path.join(images_path, key + '___pixel.json'), 'w') as fw:
            json.dump(sa_js, fw, indent=2)
