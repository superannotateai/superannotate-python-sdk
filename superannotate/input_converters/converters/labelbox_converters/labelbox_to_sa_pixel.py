from pathlib import Path
import cv2
import numpy as np

from .labelbox_helper import (
    image_downloader, _create_classes_json, _create_classes_id_map,
    _create_attributes_list
)

from ..sa_json_helper import _create_pixel_instance

from ....common import hex_to_rgb, blue_color_generator


def labelbox_instance_segmentation_to_sa_pixel(json_data):
    classes = _create_classes_id_map(json_data)
    sa_jsons = {}
    sa_masks = {}
    for d in json_data:
        file_name = d['External ID'] + '___pixel.json'
        mask_name = d['External ID'] + '___save.png'
        if 'objects' not in d['Label'].keys():
            sa_jsons[file_name] = []
            continue

        instances = d["Label"]["objects"]
        sa_loader = []
        blue_colors = blue_color_generator(len(instances))

        for i, instance in enumerate(instances):
            class_name = instance["value"]
            attributes = []
            if 'classifications' in instance.keys():
                attributes = _create_attributes_list(
                    instance['classifications']
                )

            if 'bbox' in instance.keys() or 'polygon' in instance.keys(
            ) or 'line' in instance.keys() or 'point' in instance.keys():
                continue

            image_downloader(instance['instanceURI'], mask_name)
            mask = cv2.imread(mask_name)
            if i == 0:
                H, W, C = mask.shape
                sa_mask = np.zeros((H, W, C + 1))
            sa_mask[np.all(mask == [255, 255, 255], axis=2)
                   ] = list(hex_to_rgb(blue_colors[i]))[::-1] + [255]

            parts = [{'color': blue_colors[i]}]
            sa_obj = _create_pixel_instance(parts, attributes, class_name)

            sa_loader.append(sa_obj.copy())
            Path(mask_name).unlink()

        sa_jsons[file_name] = sa_loader
        sa_masks[mask_name] = sa_mask

    sa_classes = _create_classes_json(classes)
    return sa_jsons, sa_classes, sa_masks
