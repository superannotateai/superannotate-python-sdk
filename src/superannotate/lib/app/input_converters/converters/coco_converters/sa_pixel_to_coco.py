import cv2 as cv
import numpy as np

from .coco_api import _area
from .coco_api import _toBbox


def __instance_object_commons_per_instance(instance, id_generator, flat_mask):
    if "parts" not in instance:
        return None

    anno_id = next(id_generator)
    parts = [int(part["color"][1:], 16) for part in instance["parts"]]
    category_id = instance["classId"]

    instance_bitmask = np.isin(flat_mask, parts)

    databytes = instance_bitmask * np.uint8(255)
    contours, _ = cv.findContours(databytes, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_NONE)
    bbox = list(_toBbox(instance_bitmask))
    area = int(_area(instance_bitmask.astype(np.uint8)))
    return (bbox, area, contours, category_id, anno_id)


def instance_object_commons(instances, id_generator, flat_mask):
    commons_lst = [
        __instance_object_commons_per_instance(x, id_generator, flat_mask)
        for x in instances
    ]
    commons_lst = [x for x in commons_lst if x is not None]
    return commons_lst
