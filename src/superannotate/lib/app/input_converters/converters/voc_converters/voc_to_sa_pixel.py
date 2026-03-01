"""
VOC to SA conversion method
"""
import logging

import cv2
import numpy as np

from ....common import blue_color_generator
from ....common import hex_to_rgb
from .voc_helper import _iou

logger = logging.getLogger("sa")


def _generate_polygons(object_mask_path):
    segmentation = []

    object_mask = cv2.imread(str(object_mask_path), cv2.IMREAD_GRAYSCALE)

    object_unique_colors = np.unique(object_mask)

    num_colors = len([i for i in object_unique_colors if i not in (0, 220)])
    bluemask_colors = blue_color_generator(num_colors)
    H, W = object_mask.shape
    sa_mask = np.zeros((H, W, 4))
    i = 0
    for unique_color in object_unique_colors:
        if unique_color in (0, 220):
            continue

        mask = np.zeros_like(object_mask)
        mask[object_mask == unique_color] = 255
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        segment = []
        for contour in contours:
            contour = contour.flatten().tolist()
            segment += contour
        if len(contour) > 4:
            segmentation.append(segment)
        if len(segmentation) == 0:
            continue

        sa_mask[object_mask == unique_color] = [255] + list(
            hex_to_rgb(bluemask_colors[i])
        )
        i += 1
    return segmentation, sa_mask, bluemask_colors


def _generate_instances(polygon_instances, voc_instances, bluemask_colors):
    instances = []
    i = 0
    for polygon in polygon_instances:
        ious = []
        bbox_poly = [
            min(polygon[::2]),
            min(polygon[1::2]),
            max(polygon[::2]),
            max(polygon[1::2]),
        ]
        for _, bbox in voc_instances:
            ious.append(_iou(bbox_poly, bbox))
        ind = np.argmax(ious)
        class_name = list(voc_instances[ind][0].keys())[0]
        attributes = voc_instances[ind][0][class_name]
        instances.append(
            {
                "className": class_name,
                "polygon": polygon,
                "bbox": voc_instances[ind][1],
                "blue_color": bluemask_colors[i],
                "classAttributes": attributes,
            }
        )
        i += 1
    return instances
