import json
import logging
from pathlib import Path

import cv2
import numpy as np
from tqdm import tqdm

from .coco_api import (_maskfrRLE, decode)

from ....common import blue_color_generator, hex_to_rgb, id2rgb

logger = logging.getLogger("superannotate-python-sdk")


def annot_to_bitmask(annot):
    if isinstance(annot['counts'], list):
        bitmask = _maskfrRLE(annot)
    elif isinstance(annot['counts'], str):
        bitmask = decode(annot)

    return bitmask


def coco_panoptic_segmentation_to_sa_pixel(coco_path, images_path):
    coco_json = json.load(open(coco_path))
    hex_colors = blue_color_generator(len(coco_json["categories"]))
    annotate_list = coco_json["annotations"]

    cat_id_to_cat = {}
    for cat in coco_json['categories']:
        cat_id_to_cat[cat['id']] = cat['name']

    sa_jsons = {}
    for annotate in tqdm(annotate_list, "Converting annotations"):
        annot_name = Path(annotate["file_name"]).stem
        img_cv = cv2.imread(str(images_path / (annot_name + ".png")))
        if img_cv is None:
            logger.warning(
                "'{}' file dosen't exist!".format(
                    images_path / (annot_name + ".png")
                )
            )
            continue

        img = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
        H, W, C = img.shape
        img = img.reshape((H * W, C))
        segments = annotate["segments_info"]
        hex_colors = blue_color_generator(len(segments))

        out_json = []
        for i, seg in enumerate(segments):
            img[np.all(img == id2rgb(seg["id"]),
                       axis=1)] = hex_to_rgb(hex_colors[i])
            dd = {
                "classId": seg["category_id"],
                'className': cat_id_to_cat[seg["category_id"]],
                "probability": 100,
                "visible": True,
                "parts": [{
                    "color": hex_colors[i]
                }],
                "attributes": [],
                "attributeNames": [],
                "imageId": annotate["image_id"]
            }
            out_json.append(dd)

        img = cv2.cvtColor(img.reshape((H, W, C)), cv2.COLOR_RGB2BGR)
        cv2.imwrite(str(images_path / (annot_name + ".jpg___save.png")), img)

        file_name = annot_name + ".jpg___pixel.json"
        sa_jsons[file_name] = out_json
        (images_path / (annot_name + ".png")).unlink()
    return sa_jsons


def coco_instance_segmentation_to_sa_pixel(coco_path, images_path):
    coco_json = json.load(open(coco_path))
    cat_id_to_cat = {}
    for cat in coco_json['categories']:
        cat_id_to_cat[cat['id']] = cat

    images_dict = {}
    for img in coco_json['images']:
        images_dict[img['id']] = {
            'shape': (img['height'], img['width'], 4),
            'file_name': img['file_name'],
            'annotations': []
        }

    for annot in coco_json['annotations']:
        if annot['image_id'] not in images_dict:
            continue
        images_dict[annot['image_id']]['annotations'].append(annot)

    sa_jsons = {}
    for id_, annotations in images_dict.items():
        file_name = annotations['file_name'] + '___pixel.json'
        hexcolors = blue_color_generator(len(annotations['annotations']))
        mask = np.zeros(annotations['shape'])
        H, W, _ = mask.shape

        sa_loader = []
        for i, annot in enumerate(annotations['annotations']):
            hexcolor = hexcolors[i]
            color = hex_to_rgb(hexcolor)
            if isinstance(annot['segmentation'], dict):
                bitmask = annot_to_bitmask(annot['segmentation'])
                mask[bitmask == 1] = list(color)[::-1] + [255]
            else:
                for segment in annot['segmentation']:
                    bitmask = np.zeros((H, W)).astype(np.uint8)
                    pts = np.array(
                        [
                            segment[2 * i:2 * (i + 1)]
                            for i in range(len(segment) // 2)
                        ],
                        dtype=np.int32
                    )
                    cv2.fillPoly(bitmask, [pts], 1)
                    mask[bitmask == 1] = list(color)[::-1] + [255]

            sa_obj = {
                "className": cat_id_to_cat[annot['category_id']]['name'],
                'probability': 100,
                'visible': True,
                'parts': [{
                    'color': hexcolor
                }],
                "attributes": [],
                "attributeNames": [],
            }
            sa_loader.append(sa_obj.copy())
        sa_jsons[file_name] = sa_loader
        cv2.imwrite(
            str(images_path / (annotations['file_name'] + '___save.png')), mask
        )

    return sa_jsons
