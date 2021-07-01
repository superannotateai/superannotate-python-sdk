import cv2 as cv
import numpy as np

from .coco_api import _area, _toBbox


def __instance_object_commons_per_instance(instance, id_generator, flat_mask):
    if "parts" not in instance:
        return None

    anno_id = next(id_generator)
    parts = [int(part["color"][1:], 16) for part in instance["parts"]]
    category_id = instance['classId']

    instance_bitmask = np.isin(flat_mask, parts)

    databytes = instance_bitmask * np.uint8(255)
    contours, _ = cv.findContours(
        databytes, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_NONE
    )
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


def sa_pixel_to_coco_instance_segmentation(
    make_annotation, image_commons, instances, id_generator
):
    commons_lst = instance_object_commons(
        instances, id_generator, image_commons.flat_mask
    )
    image_info = image_commons.image_info
    annotations_per_image = []
    for common in commons_lst:
        bbox, area, contours, category_id, anno_id = common
        segmentation = [
            contour.flatten().tolist()
            for contour in contours if len(contour.flatten().tolist()) >= 5
        ]

        if segmentation != []:
            annotations_per_image.append(
                make_annotation(
                    category_id, image_info['id'], bbox, segmentation, area,
                    anno_id
                )
            )

    return (image_info, annotations_per_image)


def sa_pixel_to_coco_panoptic_segmentation(
    image_commons, instnaces, id_generator
):
    flat_mask = image_commons.flat_mask
    ann_mask = image_commons.ann_mask

    segments_info = []

    for instance in instnaces:
        if 'parts' not in instance:
            continue

        parts = [int(part['color'][1:], 16) for part in instance['parts']]
        category_id = instance['classId']
        instance_bitmask = np.isin(flat_mask, parts)
        segment_id = next(id_generator)
        ann_mask[instance_bitmask] = segment_id
        bbox = list(_toBbox(instance_bitmask))
        area = int(_area(instance_bitmask.astype(np.uint8)))

        segment_info = {
            'id': segment_id,
            'category_id': category_id,
            'area': area,
            'bbox': bbox,
            'iscrowd': 0
        }

        segments_info.append(segment_info)

    return (image_commons.image_info, segments_info, image_commons.ann_mask)
