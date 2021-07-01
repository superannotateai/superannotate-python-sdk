'''
COCO to SA conversion method
'''

import json
import logging
import threading
from pathlib import Path

import cv2
import numpy as np

from .coco_api import _maskfrRLE, decode
from ..sa_json_helper import _create_pixel_instance, _create_sa_json
from ....common import (
    blue_color_generator, hex_to_rgb, id2rgb, write_to_json, tqdm_converter
)

logger = logging.getLogger("superannotate-python-sdk")


def annot_to_bitmask(annot):
    if isinstance(annot['counts'], list):
        bitmask = _maskfrRLE(annot)
    elif isinstance(annot['counts'], str):
        bitmask = decode(annot)

    return bitmask


def coco_panoptic_segmentation_to_sa_pixel(coco_path, output_dir):
    coco_json = json.load(open(coco_path))
    hex_colors = blue_color_generator(len(coco_json["categories"]))

    cat_id_to_cat = {}
    for cat in coco_json['categories']:
        cat_id_to_cat[cat['id']] = cat['name']

    img_id_to_shape = {}
    for img in coco_json['images']:
        img_id_to_shape[str(img['id'])] = {
            'height': img['height'],
            'width': img['width']
        }

    images_converted = []
    images_not_converted = []
    finish_event = threading.Event()
    tqdm_thread = threading.Thread(
        target=tqdm_converter,
        args=(
            len(coco_json["annotations"]), images_converted,
            images_not_converted, finish_event
        ),
        daemon=True
    )
    logger.info('Converting to SuperAnnotate JSON format')
    tqdm_thread.start()
    for annot in coco_json["annotations"]:
        annot_name = Path(annot["file_name"]).stem
        img_cv = cv2.imread(str(output_dir / ("%s.png" % annot_name)))
        if img_cv is None:
            images_not_converted.append(annot['file_name'])
            logger.warning(
                "'%s' file dosen't exist!",
                output_dir / ("%s.png" % annot_name)
            )
            continue

        img = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
        H, W, C = img.shape
        img = img.reshape((H * W, C))
        segments = annot["segments_info"]
        hex_colors = blue_color_generator(len(segments))

        sa_instances = []
        for i, seg in enumerate(segments):
            img[np.all(img == id2rgb(seg["id"]),
                       axis=1)] = hex_to_rgb(hex_colors[i])
            parts = [{'color': hex_colors[i]}]
            sa_obj = _create_pixel_instance(
                parts, [], cat_id_to_cat[seg["category_id"]]
            )
            sa_instances.append(sa_obj)

        img = cv2.cvtColor(img.reshape((H, W, C)), cv2.COLOR_RGB2BGR)
        cv2.imwrite(
            str(output_dir / ("%s___save.png" % annot['file_name'])), img
        )

        images_converted.append(annot['file_name'])
        file_name = "%s___pixel.json" % annot['file_name']
        sa_metadata = {
            'name': annot_name,
            'width': img_id_to_shape[str(annot['image_id'])]['width'],
            'height': img_id_to_shape[str(annot['image_id'])]['height']
        }
        json_template = _create_sa_json(sa_instances, sa_metadata)
        write_to_json(output_dir / file_name, json_template)
        (output_dir / ("%s.png" % annot_name)).unlink()
    finish_event.set()
    tqdm_thread.join()


def coco_instance_segmentation_to_sa_pixel(coco_path, output_dir):
    coco_json = json.load(open(coco_path))
    cat_id_to_cat = {}
    for cat in coco_json['categories']:
        cat_id_to_cat[cat['id']] = cat

    images_dict = {}
    for img in coco_json['images']:
        images_dict[int(img['id'])] = {
            'shape': (img['height'], img['width'], 4),
            'file_name': img['file_name'],
            'annotations': []
        }

    for annot in coco_json['annotations']:
        if int(annot['image_id']) not in images_dict:
            continue
        images_dict[annot['image_id']]['annotations'].append(annot)

    images_converted = []
    images_not_converted = []
    finish_event = threading.Event()
    tqdm_thread = threading.Thread(
        target=tqdm_converter,
        args=(
            len(images_dict.items()), images_converted, images_not_converted,
            finish_event
        ),
        daemon=True
    )
    logger.info('Converting to SuperAnnotate JSON format')
    tqdm_thread.start()
    for id_, annotations in images_dict.items():
        file_name = '%s___pixel.json' % annotations['file_name']
        hexcolors = blue_color_generator(len(annotations['annotations']))
        mask = np.zeros(annotations['shape'])
        H, W, _ = mask.shape

        sa_instances = []
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

            parts = [{'color': hexcolor}]
            sa_obj = _create_pixel_instance(
                parts, [], cat_id_to_cat[annot['category_id']]['name']
            )
            sa_instances.append(sa_obj)

        sa_metadata = {
            'name': images_dict[id_]['file_name'],
            'width': images_dict[id_]['shape'][1],
            'height': images_dict[id_]['shape'][0]
        }
        images_converted.append(annotations['file_name'])
        json_template = _create_sa_json(sa_instances, sa_metadata)
        write_to_json(output_dir / file_name, json_template)
        cv2.imwrite(
            str(output_dir / ('%s___save.png' % annotations['file_name'])), mask
        )
    finish_event.set()
    tqdm_thread.join()
